import os
import asyncio
from fastapi import Response
import aiohttp
import requests

from app.models.hyperloop_download import HyperloopDownload

class NiFiUploader:
    def __init__(self):
        self.endpoint_url = os.getenv("NIFI_LISTEN_HTTP_ENDPONT", "http://localhost:9099/hyperloop")

    async def send_tarball(self, tarball_path: str, dependency: HyperloopDownload) -> Response:
        """
        Sends the tarball to the HTTP endpoint with the specified dependency and type as headers.
        
        :param tarball_path: Path to the tarball file to be sent.
        :param dependency: Dependency information to be sent in the headers.
        :return: Response object from the HTTP request.
        """
        headers = {
            "hyperloop.dependency": dependency.dependency,
            "hyperloop.type": dependency.type
        }
        print(f"Sending tarball {tarball_path} to {self.endpoint_url} with headers: {headers}")

        try:
            timeout = aiohttp.ClientTimeout(total=600)  # 10 minute timeout for large files
            async with aiohttp.ClientSession(timeout=timeout) as session:
                with open(tarball_path, "rb") as tarball:
                    filename = os.path.basename(tarball_path)
                    data = aiohttp.FormData()
                    data.add_field('file', tarball, filename=filename)
                    
                    async with session.post(self.endpoint_url, headers=headers, data=data) as response:
                        response_text = await response.text()
                        
                        # Create a mock response object similar to requests.Response
                        mock_response = type('MockResponse', (), {
                            'status_code': response.status,
                            'text': response_text
                        })()

                        if response.status == 200:
                            print(f"Tarball {tarball_path} sent successfully!")
                            return mock_response
                        else:
                            print(f"Failed to send tarball: {response.status}, {response_text}")
                            return mock_response
        except Exception as e:
            print(f"Error sending tarball: {e}")
            raise