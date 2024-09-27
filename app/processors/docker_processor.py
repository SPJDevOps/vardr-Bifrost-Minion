import json
import os
import re
from aio_pika import Message
import docker
import requests

from app.models.download_status import DownloadStatus
from app.models.hyperloop_download import HyperloopDownload

class DockerProcessor:
    def __init__(self, rabbitmq, status_queue):
        self.rabbitmq = rabbitmq
        self.status_queue = status_queue
        self.docker_client = docker.from_env()
        self.temp_dir = "/tmp/docker-images/"


    async def process(self, download: HyperloopDownload):
        await self.download_step(download)
        await self.packaging_step(download)
        await self.sending_step(download)


    def sanitize_filename(self, filename: str) -> str:
        # Replace forward slashes, colons, and any non-alphanumeric characters with underscores
        return re.sub(r'[\/:]', '_', filename)


    async def download_step(self, download: HyperloopDownload):
        print(f"Executing step 1 for {download.type}...")
        download.status = DownloadStatus.DOWNLOADING
        await self.publish_status_update(download)
        docker_image = download.dependency
        print(f"Step 1: Pulling Docker image {docker_image}...")

        try:
            self.docker_client.images.pull(docker_image)
            print(f"Docker image {docker_image} downloaded successfully.")
        except docker.errors.APIError as e:
            print(f"Error pulling Docker image {docker_image}: {e}")
            download.status = DownloadStatus.FAILED
            await self.publish_status_update(download)
            return
        

    async def packaging_step(self, download: HyperloopDownload):
        print(f"Executing step 2 for {download.type}...")
        download.status = DownloadStatus.SENDING
        await self.publish_status_update(download)
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
        # Send the tarball to the HTTP endpoint
        tarball_name = download.tarball_path
        endpoint_url = "http://localhost:9998/"
        headers = {"hyperloop.dependency": download.dependency, "hyperloop.type": download.type}
        print(f"Step 3: Sending tarball {tarball_name} to {endpoint_url} with dependency {download.dependency}...")

        try:
            with open(tarball_name, "rb") as tarball:
                # Send the tarball via HTTP POST
                response = requests.post(endpoint_url, headers=headers, files={"file": tarball})

            if response.status_code == 200:
                print(f"Tarball {tarball_name} sent successfully!")
                download.status = DownloadStatus.DONE
            else:
                print(f"Failed to send tarball: {response.status_code}, {response.text}")
                download.status = DownloadStatus.FAILED
        except Exception as e:
            print(f"Error sending tarball: {e}")
            download.status = DownloadStatus.FAILED

        # Publish the final status
        await self.publish_status_update(download)

    async def publish_status_update(self, download: HyperloopDownload):
        message_body = json.dumps(download.to_dict())
        await self.rabbitmq.channel.default_exchange.publish(
            Message(body=message_body.encode()),
            routing_key=self.status_queue
        )
        print(f"Published to {self.status_queue} with status: {download.status}")