import os
import requests
import tarfile
import yaml
import tempfile
from urllib.parse import urljoin

from app.helpers.nifi_uploader import NiFiUploader
from app.helpers.status_publisher import publish_status_update
from app.models.download_status import DownloadStatus
from app.models.hyperloop_download import HyperloopDownload

class HelmChartProcessor:
    def __init__(self, rabbitmq, status_queue):
        self.rabbitmq = rabbitmq
        self.status_queue = status_queue
        self.temp_dir = "/tmp/helm-charts/"  # Directory to store downloaded Helm charts
        self.tarball_sender = NiFiUploader("http://localhost:9998/")  # Initialize TarballSender

        # Ensure the temp directory exists
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    async def process(self, download: HyperloopDownload):
        # Download step
        await self.download_step(download)
        # Packaging step
        await self.packaging_step(download)
        # Sending step
        await self.sending_step(download)

    async def download_step(self, download: HyperloopDownload):
        """Download the Helm chart tarballs from the index.yaml and extract Docker images."""
        index_url = download.dependency  # The URL to the index.yaml file
        index_filename = os.path.join(self.temp_dir, "index.yaml")
        chart_dir = os.path.join(self.temp_dir, "charts")

        if not os.path.exists(chart_dir):
            os.makedirs(chart_dir)

        print(f"Downloading Helm chart index from {index_url}...")

        try:
            # Download the index.yaml file
            response = requests.get(index_url)
            response.raise_for_status()

            # Save the index.yaml file
            with open(index_filename, "wb") as file:
                file.write(response.content)
            print(f"index.yaml downloaded and saved at {index_filename}.")

            # Parse the index.yaml file
            with open(index_filename, "r") as stream:
                index_data = yaml.safe_load(stream)

            # Download the latest version of each Helm chart and extract Docker images
            for chart_name, chart_versions in index_data.get('entries', {}).items():
                latest_version_info = chart_versions[0]  # Latest version is the first in the list
                chart_url = urljoin(index_url, latest_version_info['urls'][0])  # Full URL to the chart tarball
                chart_filename = os.path.join(chart_dir, f"{chart_name}-{latest_version_info['version']}.tgz")

                print(f"Downloading Helm chart {chart_name} (version {latest_version_info['version']}) from {chart_url}...")

                # Download the Helm chart tarball
                chart_response = requests.get(chart_url)
                chart_response.raise_for_status()

                # Save the Helm chart tarball
                with open(chart_filename, "wb") as chart_file:
                    chart_file.write(chart_response.content)
                print(f"Helm chart {chart_name} saved at {chart_filename}.")

                # Extract the chart tarball to a temporary directory
                with tempfile.TemporaryDirectory() as temp_chart_dir:
                    with tarfile.open(chart_filename, "r:gz") as tar:
                        tar.extractall(temp_chart_dir)

                    # Find and extract Docker images from the chart templates
                    await self.extract_docker_images(temp_chart_dir)

        except requests.RequestException as e:
            print(f"Error downloading Helm charts from {index_url}: {e}")
            download.status = DownloadStatus.FAILED
            await publish_status_update(self.rabbitmq, self.status_queue, download)
            return

        # Set the status to DOWNLOADING
        download.status = DownloadStatus.DOWNLOADING
        download.package_dir = chart_dir  # Save the charts directory for later use
        await publish_status_update(self.rabbitmq, self.status_queue, download)

    async def extract_docker_images(self, chart_dir):
        """Extract Docker images from Helm chart templates and send them via HTTP POST."""
        templates_dir = os.path.join(chart_dir, "templates")

        if not os.path.exists(templates_dir):
            print(f"No templates directory found in the chart at {chart_dir}")
            return

        # Iterate over all template files in the chart
        for root, dirs, files in os.walk(templates_dir):
            for file in files:
                template_path = os.path.join(root, file)
                if file.endswith(".yaml") or file.endswith(".tpl"):
                    with open(template_path, "r") as template_file:
                        try:
                            template_data = yaml.safe_load(template_file)
                        except yaml.YAMLError:
                            print(f"Error parsing template file: {template_path}")
                            continue

                        # Check for Kubernetes resources with container specs
                        if isinstance(template_data, dict) and "kind" in template_data:
                            if template_data["kind"] in ["Deployment", "StatefulSet", "DaemonSet", "Pod"]:
                                containers = template_data.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
                                for container in containers:
                                    image = container.get("image")
                                    if image:
                                        print(f"Found Docker image: {image}")
                                        # Send the Docker image as an HTTP POST request
                                        await self.send_docker_image_to_download(image)

    async def send_docker_image_to_download(self, image):
        """Send the Docker image to the /downloads endpoint via HTTP POST."""
        url = "http://localhost:8080/downloads"
        payload = {
            "type": "DOCKER",
            "dependency": image
        }

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            print(f"Successfully sent Docker image {image} to {url}")
        except requests.RequestException as e:
            print(f"Error sending Docker image {image} to {url}: {e}")

    async def packaging_step(self, download: HyperloopDownload):
        """Create a tarball of the downloaded Helm charts."""
        tarball_name = "helm-charts.tar"
        tarball_path = os.path.join(self.temp_dir, tarball_name)

        print(f"Creating tarball for downloaded Helm charts...")

        try:
            # Create the tarball from the downloaded charts
            with tarfile.open(tarball_path, "w") as tarball:
                tarball.add(download.package_dir, arcname=os.path.basename(download.package_dir))
            print(f"Tarball created at {tarball_path}.")
        except Exception as e:
            print(f"Error creating tarball for Helm charts: {e}")
            download.status = DownloadStatus.FAILED
            await publish_status_update(self.rabbitmq, self.status_queue, download)
            return

        # Attach the tarball path to the download object
        download.tarball_path = tarball_path

        # Set the status to SENDING
        download.status = DownloadStatus.SENDING
        await publish_status_update(self.rabbitmq, self.status_queue, download)

    async def sending_step(self, download: HyperloopDownload):
        """Send the tarball to the HTTP endpoint."""
        tarball_path = download.tarball_path

        try:
            # Use the TarballSender to send the tarball, passing both dependency (index.yaml URL) and type
            response = self.tarball_sender.send_tarball(tarball_path, download.dependency, download.type)
            if response.status_code == 200:
                download.status = DownloadStatus.DONE
            else:
                download.status = DownloadStatus.FAILED
        except Exception as e:
            download.status = DownloadStatus.FAILED

        # Publish the final status using the common status publisher
        await publish_status_update(self.rabbitmq, self.status_queue, download)
    
    def cleanup_temp_files(self, download: HyperloopDownload):
        """Clean up the temporary files and directories after processing."""
        try:
            if os.path.exists(download.package_dir):
                print(f"Cleaning up temporary files at {download.package_dir}")
                shutil.rmtree(download.package_dir)
        except Exception as e:
            print(f"Error during cleanup of temporary files: {e}")