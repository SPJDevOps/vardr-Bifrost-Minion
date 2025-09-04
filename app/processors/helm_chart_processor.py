import os
import asyncio
import aiohttp
import yaml
from app.processors.base_processor import BaseProcessor
from app.models.exceptions import DependencyNotFoundError, InternalError


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
            timeout = aiohttp.ClientTimeout(total=600)  # 10 minute timeout for large files
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Download the index.yaml file
                async with session.get(index_url) as response:
                    response.raise_for_status()
                    index_text = await response.text()

                # Parse the index.yaml file
                index_data = yaml.safe_load(index_text)

                # Download the latest version of each Helm chart
                for chart_name, chart_versions in index_data.get('entries', {}).items():
                    if chart_versions:
                        latest_version_info = chart_versions[0]  # Latest version is the first
                        chart_url = latest_version_info['urls'][0]
                        chart_filename = os.path.join(chart_dir, f"{chart_name}-{latest_version_info['version']}.tgz")

                        print(f"Downloading Helm chart {chart_name} (version {latest_version_info['version']})...")

                        # Download the Helm chart tarball
                        async with session.get(chart_url) as chart_response:
                            chart_response.raise_for_status()

                            # Save the Helm chart tarball
                            with open(chart_filename, "wb") as chart_file:
                                async for chunk in chart_response.content.iter_chunked(8192):
                                    chart_file.write(chunk)
                        print(f"Helm chart {chart_name} saved.")

            download.package_dir = chart_dir
            
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                raise DependencyNotFoundError(f"Helm chart index not found at URL: {index_url}")
            else:
                raise InternalError(f"HTTP error downloading Helm charts: {str(e)}")
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise InternalError(f"Network error downloading Helm charts: {str(e)}")
        except yaml.YAMLError as e:
            raise InternalError(f"Error parsing Helm chart index: {str(e)}") 