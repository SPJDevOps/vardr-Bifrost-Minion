import os
import re
import subprocess
import tarfile
import shutil
from app.helpers.nifi_uploader import NiFiUploader
from app.helpers.status_publisher import publish_status_update
from app.models.download_status import DownloadStatus
from app.models.hyperloop_download import HyperloopDownload

class MavenProcessor:
    def __init__(self, rabbitmq, status_queue):
        self.rabbitmq = rabbitmq
        self.status_queue = status_queue
        self.tarball_sender = NiFiUploader()
        self.temp_dir = "/tmp/maven-packages/"
        self.maven_home = "/path/to/maven/home"  # Update this with the correct Maven home
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    async def process(self, download: HyperloopDownload):
        # Download step
        await self.download_step(download)
        if download.status == DownloadStatus.FAILED:
            print(f"Download step failed for {download.dependency}, stopping process.")
            self.cleanup_temp_files(download)
            return  # Exit the process method if download failed

        # Packaging step
        await self.packaging_step(download)
        if download.status == DownloadStatus.FAILED:
            print(f"Packaging step failed for {download.dependency}, stopping process.")
            self.cleanup_temp_files(download)
            return  # Exit the process method if packaging failed

        # Sending step
        await self.sending_step(download)
        if download.status == DownloadStatus.FAILED:
            print(f"Sending step failed for {download.dependency}, stopping process.")
            self.cleanup_temp_files(download)
            return  # Exit the process method if sending failed

        # Cleanup step
        self.cleanup_temp_files(download)

    async def download_step(self, download: HyperloopDownload):
        """Use Maven to download the artifact and its dependencies."""
        # Set the status to DOWNLOADING
        download.status = DownloadStatus.DOWNLOADING
        await publish_status_update(self.rabbitmq, self.status_queue, download)
        
        dependency = download.dependency  # Maven coordinate, e.g., "group:artifact:version"
        group_id, artifact_id, version = dependency.split(":")
        group_path = group_id.replace(".", "/")

        # Create a directory for this artifact
        download_dir = os.path.join(self.temp_dir, self.sanitize_filename(dependency))
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        print(f"Starting download of Maven artifact and dependencies for {dependency} using Maven...")

        try:
            subprocess.run(
                [
                    "mvn",
                    "dependency:get",
                    "-Dartifact=" + dependency,
                    "-Dmaven.repo.local=" + download_dir,
                    "-DincludeScope=runtime",
                ],
                check=True,
            )

            download.package_dir = download_dir  # Save the download directory for later use
            
        except subprocess.CalledProcessError as e:
            print(f"Error downloading Maven artifact using Maven: {e}")
            download.status = DownloadStatus.FAILED
            await publish_status_update(self.rabbitmq, self.status_queue, download)
    
    def get_maven_dependencies(self, pom_path: str, download_dir: str):
        """Retrieve the list of dependencies from a POM file using Maven."""
        dependencies_file = os.path.join(download_dir, "dependencies.txt")
        
        # Update the Maven command to output the dependencies list to the specific directory
        mvn_command = [
            'mvn', 
            'dependency:list', 
            '-f', pom_path,
            f'-DoutputFile={dependencies_file}'
        ]
        
        try:
            subprocess.run(mvn_command, check=True)
            print("Dependencies list generated successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error generating dependencies list: {e}")
            return []

        # Parse the dependencies from the generated dependencies.txt file
        dependencies = []
        dependency_pattern = re.compile(r'^\[INFO\]\s+(.+):(.+):(.+):(.+):(.+)$')
        
        if os.path.exists(dependencies_file):
            with open(dependencies_file, 'r') as f:
                for line in f:
                    match = dependency_pattern.match(line)
                    if match:
                        group_id, artifact_id, _type, version, scope = match.groups()
                        dependencies.append({
                            'groupId': group_id,
                            'artifactId': artifact_id,
                            'version': version
                        })
            return dependencies
        else:
            print(f"Error: {dependencies_file} not found.")
            return []


    async def packaging_step(self, download: HyperloopDownload):
        """Create a tarball of the downloaded Maven artifacts."""
        tarball_name = f"{self.sanitize_filename(download.dependency)}.tar"
        tarball_path = os.path.join(self.temp_dir, tarball_name)

        print(f"Creating tarball for Maven artifacts...")

        try:
            # Create the tarball from the downloaded artifacts
            with tarfile.open(tarball_path, "w") as tarball:
                tarball.add(download.package_dir, arcname=os.path.basename(download.package_dir))
            print(f"Tarball created at {tarball_path}.")
            download.tarball_path = tarball_path

            # Set the status to SENDING
            download.status = DownloadStatus.SENDING
            await publish_status_update(self.rabbitmq, self.status_queue, download)

        except Exception as e:
            print(f"Error creating tarball for Maven artifacts: {e}")
            download.status = DownloadStatus.FAILED
            await publish_status_update(self.rabbitmq, self.status_queue, download)

    async def sending_step(self, download: HyperloopDownload):
        """Send the tarball to the HTTP endpoint."""
        tarball_path = download.tarball_path

        try:
            # Use the TarballSender to send the tarball
            response = self.tarball_sender.send_tarball(tarball_path, download)
            if response.status_code == 200:
                download.status = DownloadStatus.DONE
            else:
                print(f"Failed to send tarball, status code: {response.status_code}")
                download.status = DownloadStatus.FAILED
        except Exception as e:
            print(f"Error sending tarball: {e}")
            download.status = DownloadStatus.FAILED

        await publish_status_update(self.rabbitmq, self.status_queue, download)

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize the filename for safe file saving."""
        return filename.replace("/", "_").replace(":", "_")

    def cleanup_temp_files(self, download: HyperloopDownload):
        """Clean up the temporary files and directories after processing."""
        try:
            if hasattr(download, 'package_dir') and os.path.exists(download.package_dir):
                print(f"Cleaning up Maven package directory at {download.package_dir}")
                shutil.rmtree(download.package_dir)
            if hasattr(download, 'tarball_path') and os.path.exists(download.tarball_path):
                print(f"Removing tarball at {download.tarball_path}")
                os.remove(download.tarball_path)
        except Exception as e:
            print(f"Error during cleanup of temporary files: {e}")