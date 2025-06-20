import os
import requests
from app.processors.base_processor import BaseProcessor
from app.processors.download_router import DependencyNotFoundError, InternalError


class FileDownloadProcessor(BaseProcessor):
    def __init__(self, broker, status_queue):
        super().__init__(broker, status_queue, "/tmp/file-downloads/")

    async def _download_dependency(self, download):
        """Download the file from the provided URL"""
        url = download.dependency
        file_name = os.path.basename(url)
        sanitized_name = self.sanitize_filename(file_name)
        download_path = os.path.join(self.temp_dir, sanitized_name)

        print(f"Downloading file from {url}...")

        try:
            response = requests.get(url)
            response.raise_for_status()

            with open(download_path, "wb") as file:
                file.write(response.content)
            print(f"File downloaded and saved as {download_path}.")
            download.file_path = download_path
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise DependencyNotFoundError(f"File not found at URL: {url}")
            else:
                raise InternalError(f"HTTP error downloading file: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise InternalError(f"Network error downloading file: {str(e)}") 