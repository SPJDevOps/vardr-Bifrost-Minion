import os
import requests
import tarfile

from app.helpers.nifi_uploader import NiFiUploader
from app.helpers.status_publisher import publish_status_update
from app.models.download_status import DownloadStatus
from app.models.hyperloop_download import HyperloopDownload

class FileDownloadProcessor:
    def __init__(self, rabbitmq, status_queue):
        self.rabbitmq = rabbitmq
        self.status_queue = status_queue
        self.temp_dir = "/tmp/file-downloads/"  # Directory to store downloaded files
        self.tarball_sender = NiFiUploader()  # Initialize TarballSender

        # Ensure the temp directory exists
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    async def process(self, download: HyperloopDownload):
        # Download step
        await self.download_step(download)
        # Packaging step
        await self.packaging_step(download)
        # Sending step
        await self.sending_step(download)
        self.cleanup_temp_files(download)

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize the filename for safe file saving."""
        return filename.replace("/", "_").replace(":", "_")

    async def download_step(self, download: HyperloopDownload):
        """Download the file from the provided URL."""
        # Set the status to DOWNLOADING
        download.status = DownloadStatus.DOWNLOADING
        await publish_status_update(self.rabbitmq, self.status_queue, download)

        url = download.dependency  # The URL to download
        file_name = os.path.basename(url)
        sanitized_name = self.sanitize_filename(file_name)
        download_path = os.path.join(self.temp_dir, sanitized_name)

        print(f"Downloading file from {url}...")

        try:
            # Download the file from the URL
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for HTTP errors

            # Save the downloaded file to the temp directory
            with open(download_path, "wb") as file:
                file.write(response.content)
            print(f"File downloaded and saved as {download_path}.")
        except requests.RequestException as e:
            print(f"Error downloading file from {url}: {e}")
            download.status = DownloadStatus.FAILED
            await publish_status_update(self.rabbitmq, self.status_queue, download)
            return

        download.package_dir = download_path  # Save the download path for later use


    async def packaging_step(self, download: HyperloopDownload):
        """Create a tarball of the downloaded file."""
        file_name = os.path.basename(download.package_dir)
        sanitized_name = self.sanitize_filename(file_name)
        tarball_name = f"{sanitized_name}.tar"
        tarball_path = os.path.join(self.temp_dir, tarball_name)

        print(f"Creating tarball for downloaded file {file_name}...")

        try:
            # Create the tarball from the downloaded file
            with tarfile.open(tarball_path, "w") as tarball:
                tarball.add(download.package_dir, arcname=os.path.basename(download.package_dir))
            print(f"Tarball created at {tarball_path}.")
        except Exception as e:
            print(f"Error creating tarball for {file_name}: {e}")
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
            # Use the TarballSender to send the tarball, passing both dependency (URL) and type
            response = self.tarball_sender.send_tarball(tarball_path, download)
            if response.status_code == 200:
                download.status = DownloadStatus.DONE
            else:
                download.status = DownloadStatus.FAILED
        except Exception as e:
            download.status = DownloadStatus.FAILED

        # Publish the final status using the common status publisher
        await publish_status_update(self.rabbitmq, self.status_queue, download)
    
    def cleanup_temp_files(self, download: HyperloopDownload):
        """Clean up the temporary files and tarball after processing."""
        try:
            # Remove the downloaded file
            if os.path.exists(download.package_dir):
                print(f"Cleaning up file at {download.package_dir}")
                os.remove(download.package_dir)
            # Remove the tarball
            if os.path.exists(download.tarball_path):
                print(f"Removing tarball at {download.tarball_path}")
                os.remove(download.tarball_path)
        except Exception as e:
            print(f"Error during cleanup of temporary files: {e}")