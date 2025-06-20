import os
import subprocess
from app.processors.base_processor import BaseProcessor
from app.processors.download_router import DependencyNotFoundError, InternalError


class PythonPackageProcessor(BaseProcessor):
    def __init__(self, broker, status_queue):
        super().__init__(broker, status_queue, "/tmp/python-packages/")

    async def _download_dependency(self, download):
        """Download Python package as .whl files using pip"""
        package_name = download.dependency
        sanitized_name = self.sanitize_filename(package_name)
        download_dir = os.path.join(self.temp_dir, sanitized_name)

        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        print(f"Downloading Python package {package_name} and its dependencies...")

        try:
            subprocess.run(
                ["pip", "download", package_name, "--python-version", "3.11", "--dest", download_dir, "--only-binary=:all:", "--platform", "manylinux2014_x86_64"],
                check=True
            )
            print(f"Python package {package_name} downloaded successfully.")
            download.package_dir = download_dir
            
        except subprocess.CalledProcessError as e:
            if "Could not find a version" in str(e) or "No matching distribution" in str(e):
                raise DependencyNotFoundError(f"Python package {package_name} does not exist")
            else:
                raise InternalError(f"Python package download error: {str(e)}") 