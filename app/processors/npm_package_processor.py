import os
import asyncio
from app.processors.base_processor import BaseProcessor
from app.models.exceptions import DependencyNotFoundError, InternalError


class NpmPackageProcessor(BaseProcessor):
    def __init__(self, broker, status_queue):
        super().__init__(broker, status_queue, "/tmp/npm-packages/")

    async def _download_dependency(self, download):
        """Download NPM package tarballs using npm pack"""
        package_spec = download.dependency
        sanitized_name = self.sanitize_filename(package_spec)
        download_dir = os.path.join(self.temp_dir, sanitized_name)

        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        print(f"Downloading NPM package {package_spec}...")

        try:
            # Use asyncio.create_subprocess_exec for non-blocking subprocess calls
            process = await asyncio.create_subprocess_exec(
                "npm", "pack", package_spec,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=download_dir
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                stderr_text = stderr.decode()
                if "404" in stderr_text or "not found" in stderr_text.lower():
                    raise DependencyNotFoundError(f"NPM package {package_spec} does not exist")
                else:
                    raise InternalError(f"NPM package download error: {stderr_text}")
                    
            print(f"NPM package {package_spec} downloaded successfully.")
            download.package_dir = download_dir
            
        except asyncio.TimeoutError:
            raise InternalError(f"NPM package download timeout for {package_spec}")
        except Exception as e:
            if isinstance(e, (DependencyNotFoundError, InternalError)):
                raise
            raise InternalError(f"NPM package download error: {str(e)}") 