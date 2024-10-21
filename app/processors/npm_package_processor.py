import os
import shutil
import subprocess
import tarfile

from app.helpers.nifi_uploader import NiFiUploader
from app.helpers.status_publisher import publish_status_update
from app.models.download_status import DownloadStatus
from app.models.hyperloop_download import HyperloopDownload


class NpmPackageProcessor:
    def __init__(self, rabbitmq, status_queue):
        self.rabbitmq = rabbitmq
        self.status_queue = status_queue
        self.temp_dir = "/tmp/npm-packages/"  # Directory to store downloaded NPM tarballs
        self.tarball_sender = NiFiUploader()  # Initialize TarballSender

        # Ensure the temp directory exists
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    async def process(self, download: HyperloopDownload):
        # Step 1: Download the NPM package
        await self.download_step(download)
        # Step 2: Add to tarball
        await self.packaging_step(download)
        # Step 3: Send tarball to HTTP endpoint
        await self.sending_step(download)
        # Cleanup step
        self.cleanup_temp_files(download)

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize the filename for safe file saving."""
        return filename.replace("/", "_").replace(":", "_")

    async def download_step(self, download: HyperloopDownload):
        """Download NPM package tarballs using npm pack."""
        # Set the status to DOWNLOADING
        download.status = DownloadStatus.DOWNLOADING
        await publish_status_update(self.rabbitmq, self.status_queue, download)
        
        package_name = download.dependency
        sanitized_name = self.sanitize_filename(package_name)
        download_dir = os.path.join(self.temp_dir, sanitized_name)

        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        print(f"Step 1: Downloading NPM package {package_name} and its dependencies...")

        try:
            # Step 1: Use npm pack to download the tarball for the main package
            subprocess.run(
                ["npm", "pack", package_name],
                check=True,
                cwd=download_dir
            )
            print(f"NPM package {package_name} downloaded successfully.")

            # Step 2: Install the main package to get its dependencies
            subprocess.run(
                ["npm", "install", package_name, "--no-save"],
                check=True,
                cwd=download_dir
            )

            # Step 3: Iterate through node_modules and pack each sub-dependency
            node_modules_dir = os.path.join(download_dir, "node_modules")
            if os.path.exists(node_modules_dir):
                for sub_package in os.listdir(node_modules_dir):
                    sub_package_dir = os.path.join(node_modules_dir, sub_package)

                    # Handle the case where there may be a scope (e.g., @scope/package)
                    if os.path.isdir(sub_package_dir):
                        if sub_package.startswith("@"):
                            # For scoped packages, you need to go one level deeper
                            for scoped_sub_package in os.listdir(sub_package_dir):
                                scoped_sub_package_dir = os.path.join(sub_package_dir, scoped_sub_package)
                                self.pack_sub_dependency(scoped_sub_package_dir, download_dir)
                        else:
                            self.pack_sub_dependency(sub_package_dir, download_dir)

        except subprocess.CalledProcessError as e:
            print(f"Error downloading NPM package {package_name}: {e}")
            download.status = DownloadStatus.FAILED
            await publish_status_update(self.rabbitmq, self.status_queue, download)
            return

        download.package_dir = download_dir  # Save the package directory for later use
            

    async def packaging_step(self, download: HyperloopDownload):
        """Create a tarball of the downloaded NPM package tarballs."""
        package_name = download.dependency
        sanitized_name = self.sanitize_filename(package_name)
        tarball_name = f"{sanitized_name}.tar"
        tarball_path = os.path.join(self.temp_dir, tarball_name)

        print(f"Step 2: Creating tarball for NPM package {package_name}...")

        # Remove the node_modules directory if it exists
        node_modules_dir = os.path.join(download.package_dir, "node_modules")
        if os.path.exists(node_modules_dir):
            print(f"Removing node_modules directory at {node_modules_dir}")
            shutil.rmtree(node_modules_dir)

        try:
            # Create the tarball from the downloaded tarballs
            with tarfile.open(tarball_path, "w") as tarball:
                tarball.add(download.package_dir, arcname=os.path.basename(download.package_dir))
            print(f"Tarball created at {tarball_path}")
        except Exception as e:
            print(f"Error creating tarball for {package_name}: {e}")
            download.status = DownloadStatus.FAILED
            await publish_status_update(self.rabbitmq, self.status_queue, download)
            return

        # Attach the tarball path to the download object
        download.tarball_path = tarball_path

        # Set the status to SENDING
        download.status = DownloadStatus.SENDING
        await publish_status_update(self.rabbitmq, self.status_queue, download)

    async def sending_step(self, download: HyperloopDownload):
        """Send the tarball to the HTTP endpoint."""
        tarball_path = download.tarball_path

        try:
            # Use the TarballSender to send the tarball, passing both dependency and type
            response = self.tarball_sender.send_tarball(tarball_path, download)
            if response.status_code == 200:
                download.status = DownloadStatus.DONE
            else:
                download.status = DownloadStatus.FAILED
        except Exception as e:
            download.status = DownloadStatus.FAILED

        # Publish the final status using the common status publisher
        await publish_status_update(self.rabbitmq, self.status_queue, download)
    
    def pack_sub_dependency(self, package_dir, download_dir):
        """Packs a sub-dependency as a tarball."""
        try:
            package_name = os.path.basename(package_dir)
            print(f"Packing sub-dependency {package_name}...")

            subprocess.run(
                ["npm", "pack", package_dir],
                check=True,
                cwd=download_dir
            )
            print(f"Sub-dependency {package_name} packed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error packing sub-dependency {package_name}: {e}")
    
    def cleanup_temp_files(self, download: HyperloopDownload):
        """Clean up the temporary files and tarball after processing."""
        try:
            # Remove the NPM package directory
            if os.path.exists(download.package_dir):
                print(f"Cleaning up NPM package directory at {download.package_dir}")
                shutil.rmtree(download.package_dir)
            # Remove the tarball
            if os.path.exists(download.tarball_path):
                print(f"Removing tarball at {download.tarball_path}")
                os.remove(download.tarball_path)
        except Exception as e:
            print(f"Error during cleanup of temporary files: {e}")