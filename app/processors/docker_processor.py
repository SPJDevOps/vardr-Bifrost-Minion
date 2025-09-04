import os
import asyncio
import docker
from app.processors.base_processor import BaseProcessor
from app.models.exceptions import DependencyNotFoundError, InternalError


class DockerProcessor(BaseProcessor):
    def __init__(self, broker, status_queue):
        super().__init__(broker, status_queue, "/tmp/docker-images/")
        self.docker_client = None  # Initialize lazily when first needed

    def _get_docker_client(self):
        """Lazy initialization of Docker client"""
        if self.docker_client is None:
            self.docker_client = docker.from_env(timeout=300)  # 5 minute timeout for Docker operations
        return self.docker_client

    async def _download_dependency(self, download):
        """Download Docker image and save it as a tarball"""
        docker_image = download.dependency
        print(f"Pulling Docker image {docker_image}...")

        try:
            # Get Docker client (lazy initialization)
            client = self._get_docker_client()
            
            # Run Docker operations in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Pull the image
            await loop.run_in_executor(None, client.images.pull, docker_image)
            print(f"Docker image {docker_image} downloaded successfully.")
            
            # Save the image to a tarball
            sanitized_name = self.sanitize_filename(docker_image)
            tarball_name = f"{sanitized_name}.tar"
            tarball_path = os.path.join(self.temp_dir, tarball_name)
            
            print(f"Saving Docker image {docker_image} to tarball {tarball_path}...")
            
            # Run the save operation in thread pool
            await loop.run_in_executor(None, self._save_docker_image, docker_image, tarball_path)
            
            print(f"Docker image {docker_image} saved to tarball {tarball_path}.")
            
            # Store the tarball path directly - Docker creates final tarball, no need for packaging step
            download.tarball_path = tarball_path
            
        except docker.errors.NotFound:
            raise DependencyNotFoundError(f"Docker image {docker_image} does not exist")
        except docker.errors.APIError as e:
            raise InternalError(f"Docker API error: {str(e)}")

    def _save_docker_image(self, docker_image: str, tarball_path: str):
        """Synchronous Docker image save to be run in thread pool"""
        client = self._get_docker_client()
        image = client.images.get(docker_image)
        with open(tarball_path, "wb") as tarball_file:
            for chunk in image.save(named=True):
                tarball_file.write(chunk)

    def cleanup_temp_files(self, download):
        """Override cleanup to also remove Docker images"""
        try:
            # Remove the Docker image (only if Docker client was initialized)
            if self.docker_client is not None:
                client = self._get_docker_client()
                image = client.images.get(download.dependency)
                client.images.remove(image.id)
                print(f"Docker image {download.dependency} removed.")
        except docker.errors.ImageNotFound:
            print(f"Docker image {download.dependency} not found, skipping removal.")
        except Exception as e:
            print(f"Error removing Docker image: {e}")
        
        # Call parent cleanup
        super().cleanup_temp_files(download) 