import os
import subprocess
from app.processors.base_processor import BaseProcessor
from app.processors.download_router import DependencyNotFoundError, InternalError


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
            # Use npm pack to download the tarball
            subprocess.run(
                ["npm", "pack", package_spec],
                check=True,
                cwd=download_dir
            )
            print(f"NPM package {package_spec} downloaded successfully.")
            download.package_dir = download_dir
            
        except subprocess.CalledProcessError as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise DependencyNotFoundError(f"NPM package {package_spec} does not exist")
            else:
                raise InternalError(f"NPM package download error: {str(e)}") 