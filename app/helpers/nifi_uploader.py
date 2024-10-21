import os
from fastapi import Response
import requests

from app.models.hyperloop_download import HyperloopDownload

class NiFiUploader:
    def __init__(self):
        self.endpoint_url = os.getenv("NIFI_LISTEN_HTTP_ENDPONT", "http://localhost:9099/hyperloop")

    def send_tarball(self, tarball_path: str, dependency: HyperloopDownload) -> Response:
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
            with open(tarball_path, "rb") as tarball:
                filename = os.path.basename(tarball_path)
                # Send the tarball via HTTP POST
                response = requests.post(self.endpoint_url, headers=headers, files={"file": (filename, tarball)})

            if response.status_code == 200:
                print(f"Tarball {tarball_path} sent successfully!")
                return response
            else:
                print(f"Failed to send tarball: {response.status_code}, {response.text}")
                return response
        except Exception as e:
            print(f"Error sending tarball: {e}")
            raise