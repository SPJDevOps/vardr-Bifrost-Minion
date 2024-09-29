import os
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
        self.tarball_sender = NiFiUploader("http://localhost:9998/")  # Initialize TarballSender

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
            # Use npm pack to download the tarball for the package and its subdependencies
            subprocess.run(
                ["npm", "pack", package_name, "--prefix", download_dir],
                check=True
            )
            print(f"NPM package {package_name} downloaded successfully.")
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
            response = self.tarball_sender.send_tarball(tarball_path, download.dependency, download.type)
            if response.status_code == 200:
                download.status = DownloadStatus.DONE
            else:
                download.status = DownloadStatus.FAILED
        except Exception as e:
            download.status = DownloadStatus.FAILED

        # Publish the final status using the common status publisher
        await publish_status_update(self.rabbitmq, self.status_queue, download)