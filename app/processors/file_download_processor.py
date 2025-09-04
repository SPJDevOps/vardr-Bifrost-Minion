import os
import asyncio
import aiohttp
from app.processors.base_processor import BaseProcessor
from app.models.exceptions import DependencyNotFoundError, InternalError


class FileDownloadProcessor(BaseProcessor):
    def __init__(self, broker, status_queue):
        super().__init__(broker, status_queue, "/tmp/file-downloads/")

    async def _download_dependency(self, download):
        """Download the file from the provided URL"""
        url = download.dependency
        file_name = os.path.basename(url) or "downloaded_file"
        sanitized_name = self.sanitize_filename(file_name)
        download_path = os.path.join(self.temp_dir, sanitized_name)

        print(f"Downloading file from {url}...")

        try:
            timeout = aiohttp.ClientTimeout(total=600)  # 10 minute timeout for large files
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    
                    with open(download_path, "wb") as file:
                        async for chunk in response.content.iter_chunked(8192):
                            file.write(chunk)
                            
            print(f"File downloaded and saved as {download_path}.")
            download.file_path = download_path
            
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                raise DependencyNotFoundError(f"File not found at URL: {url}")
            else:
                raise InternalError(f"HTTP error downloading file: {str(e)}")
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise InternalError(f"Network error downloading file: {str(e)}") 