import os
import asyncio
from app.processors.base_processor import BaseProcessor
from app.models.exceptions import DependencyNotFoundError, InternalError


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
            # Use asyncio.create_subprocess_exec for non-blocking subprocess calls
            process = await asyncio.create_subprocess_exec(
                "pip", "download", package_name, 
                "--python-version", "3.11", 
                "--dest", download_dir, 
                "--only-binary=:all:", 
                "--platform", "manylinux2014_x86_64",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                stderr_text = stderr.decode()
                if "Could not find a version" in stderr_text or "No matching distribution" in stderr_text:
                    raise DependencyNotFoundError(f"Python package {package_name} does not exist")
                else:
                    raise InternalError(f"Python package download error: {stderr_text}")
                    
            print(f"Python package {package_name} downloaded successfully.")
            download.package_dir = download_dir
            
        except asyncio.TimeoutError:
            raise InternalError(f"Python package download timeout for {package_name}")
        except Exception as e:
            if isinstance(e, (DependencyNotFoundError, InternalError)):
                raise
            raise InternalError(f"Python package download error: {str(e)}") 