import os
import re
import docker

from app.helpers.nifi_uploader import NiFiUploader
from app.helpers.status_publisher import publish_status_update
from app.models.download_status import DownloadStatus
from app.models.hyperloop_download import HyperloopDownload

class DockerProcessor:
    def __init__(self, rabbitmq, status_queue):
        self.rabbitmq = rabbitmq
        self.status_queue = status_queue
        self.docker_client = docker.from_env()
        self.temp_dir = "/tmp/docker-images/"
        self.tarball_sender = NiFiUploader()

        # Ensure the directory exists
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)


    async def process(self, download: HyperloopDownload):
        await self.download_step(download)
        await self.packaging_step(download)
        await self.sending_step(download)
        self.cleanup_temp_files(download)


    def sanitize_filename(self, filename: str) -> str:
        # Replace forward slashes, colons, and any non-alphanumeric characters with underscores
        return re.sub(r'[\/:]', '_', filename)


    async def download_step(self, download: HyperloopDownload):
        print(f"Executing step 1 for {download.type}...")
        download.status = DownloadStatus.DOWNLOADING
        await publish_status_update(self.rabbitmq, self.status_queue, download)
        docker_image = download.dependency
        print(f"Step 1: Pulling Docker image {docker_image}...")

        try:
            self.docker_client.images.pull(docker_image)
            print(f"Docker image {docker_image} downloaded successfully.")
        except docker.errors.APIError as e:
            print(f"Error pulling Docker image {docker_image}: {e}")
            download.status = DownloadStatus.FAILED
            await publish_status_update(self.rabbitmq, self.status_queue, download)
            return
        

    async def packaging_step(self, download: HyperloopDownload):
        print(f"Executing step 2 for {download.type}...")
        download.status = DownloadStatus.SENDING
        await publish_status_update(self.rabbitmq, self.status_queue, download)
        docker_image = download.dependency
        sanitized_name = self.sanitize_filename(docker_image)
        tarball_name = f"{sanitized_name}.tar"
        tarball_path = os.path.join(self.temp_dir, tarball_name)

        print(f"Step 2: Saving Docker image {docker_image} to tarball {tarball_path}...")

        try:
            # Use the Docker API to save the image
            image = self.docker_client.images.get(docker_image)
            with open(tarball_path, "wb") as tarball_file:
                for chunk in image.save(named=True):
                    tarball_file.write(chunk)
            print(f"Docker image {docker_image} saved to tarball {tarball_path}.")
        except docker.errors.APIError as e:
            print(f"Error saving Docker image to tarball: {e}")
            download.status = DownloadStatus.FAILED
            await self.publish_to_queue2(download)
            return

        # Attach the tarball name to the download object
        download.tarball_path = tarball_path

    async def sending_step(self, download: HyperloopDownload):
        # Use the TarballSender to send the tarball, passing both dependency and type
        tarball_path = download.tarball_path
        try:
            response = self.tarball_sender.send_tarball(tarball_path, download)
            if response.status_code == 200:
                download.status = DownloadStatus.DONE
            else:
                download.status = DownloadStatus.FAILED
        except Exception as e:
            download.status = DownloadStatus.FAILED

        # Publish the final status
        await publish_status_update(self.rabbitmq, self.status_queue, download)

    def cleanup_temp_files(self, download: HyperloopDownload):
        """Clean up the temporary files and Docker images after processing."""
        try:
            # Remove the tarball file
            if os.path.exists(download.tarball_path):
                print(f"Removing tarball at {download.tarball_path}")
                os.remove(download.tarball_path)
            # Remove the Docker image if desired
            image = self.docker_client.images.get(download.dependency)
            self.docker_client.images.remove(image.id)
            print(f"Docker image {download.dependency} removed.")
        except docker.errors.ImageNotFound:
            print(f"Docker image {download.dependency} not found, skipping removal.")
        except Exception as e:
            print(f"Error during cleanup: {e}")
