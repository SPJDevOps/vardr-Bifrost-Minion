import os
import requests
import yaml
from app.processors.base_processor import BaseProcessor
from app.processors.download_router import DependencyNotFoundError, InternalError


class HelmChartProcessor(BaseProcessor):
    def __init__(self, broker, status_queue):
        super().__init__(broker, status_queue, "/tmp/helm-charts/")

    async def _download_dependency(self, download):
        """Download Helm chart index and charts"""
        index_url = download.dependency
        chart_dir = os.path.join(self.temp_dir, "charts")

        if not os.path.exists(chart_dir):
            os.makedirs(chart_dir)

        print(f"Downloading Helm chart index from {index_url}...")

        try:
            # Download the index.yaml file
            response = requests.get(index_url)
            response.raise_for_status()

            # Parse the index.yaml file
            index_data = yaml.safe_load(response.text)

            # Download the latest version of each Helm chart
            for chart_name, chart_versions in index_data.get('entries', {}).items():
                if chart_versions:
                    latest_version_info = chart_versions[0]  # Latest version is the first
                    chart_url = latest_version_info['urls'][0]
                    chart_filename = os.path.join(chart_dir, f"{chart_name}-{latest_version_info['version']}.tgz")

                    print(f"Downloading Helm chart {chart_name} (version {latest_version_info['version']})...")

                    # Download the Helm chart tarball
                    chart_response = requests.get(chart_url)
                    chart_response.raise_for_status()

                    # Save the Helm chart tarball
                    with open(chart_filename, "wb") as chart_file:
                        chart_file.write(chart_response.content)
                    print(f"Helm chart {chart_name} saved.")

            download.package_dir = chart_dir
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise DependencyNotFoundError(f"Helm chart index not found at URL: {index_url}")
            else:
                raise InternalError(f"HTTP error downloading Helm charts: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise InternalError(f"Network error downloading Helm charts: {str(e)}")
        except yaml.YAMLError as e:
            raise InternalError(f"Error parsing Helm chart index: {str(e)}") 