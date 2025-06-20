import os
import docker
from app.processors.base_processor import BaseProcessor
from app.processors.download_router import DependencyNotFoundError, InternalError


class DockerProcessor(BaseProcessor):
    def __init__(self, broker, status_queue):
        super().__init__(broker, status_queue, "/tmp/docker-images/")
        self.docker_client = docker.from_env()

    async def _download_dependency(self, download):
        """Download Docker image and save it as a tarball"""
        docker_image = download.dependency
        print(f"Pulling Docker image {docker_image}...")

        try:
            # Pull the image
            self.docker_client.images.pull(docker_image)
            print(f"Docker image {docker_image} downloaded successfully.")
            
            # Save the image to a tarball
            sanitized_name = self.sanitize_filename(docker_image)
            tarball_name = f"{sanitized_name}.tar"
            tarball_path = os.path.join(self.temp_dir, tarball_name)
            
            print(f"Saving Docker image {docker_image} to tarball {tarball_path}...")
            
            image = self.docker_client.images.get(docker_image)
            with open(tarball_path, "wb") as tarball_file:
                for chunk in image.save(named=True):
                    tarball_file.write(chunk)
            
            print(f"Docker image {docker_image} saved to tarball {tarball_path}.")
            
            # Store the tarball path for the base class to use
            download.file_path = tarball_path
            
        except docker.errors.NotFound:
            raise DependencyNotFoundError(f"Docker image {docker_image} does not exist")
        except docker.errors.APIError as e:
            raise InternalError(f"Docker API error: {str(e)}")

    def cleanup_temp_files(self, download):
        """Override cleanup to also remove Docker images"""
        try:
            # Remove the Docker image
            image = self.docker_client.images.get(download.dependency)
            self.docker_client.images.remove(image.id)
            print(f"Docker image {download.dependency} removed.")
        except docker.errors.ImageNotFound:
            print(f"Docker image {download.dependency} not found, skipping removal.")
        except Exception as e:
            print(f"Error removing Docker image: {e}")
        
        # Call parent cleanup
        super().cleanup_temp_files(download) 