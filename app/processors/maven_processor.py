import os
import re
import shutil
import requests
import tarfile
import xml.etree.ElementTree as ET

from app.helpers.nifi_uploader import NiFiUploader
from app.helpers.status_publisher import publish_status_update
from app.models.download_status import DownloadStatus
from app.models.hyperloop_download import HyperloopDownload


class MavenProcessor:
    def __init__(self, rabbitmq, status_queue):
        self.rabbitmq = rabbitmq
        self.status_queue = status_queue
        self.maven_base_url = "https://repo1.maven.org/maven2/"
        self.tarball_sender = NiFiUploader("http://localhost:9998/")
        self.downloaded_artifacts = set()  # To avoid re-downloading the same artifact
        self.temp_dir = "/tmp/maven-packages/"  # Directory to store downloaded artifacts

        # Ensure the temp directory exists
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    async def process(self, download: HyperloopDownload):
        # Step 1: Download the Maven artifact
        await self.download_step(download)
        # Step 2: Add to tarball
        await self.packaging_step(download)
        # Step 3: Send tarball to HTTP endpoint
        await self.sending_step(download)
        self.cleanup_temp_files(download)

    def sanitize_filename(self, filename: str) -> str:
        # Replace forward slashes, colons, and any non-alphanumeric characters with underscores
        return re.sub(r'[\/:]', '_', filename)

    def get_maven_url(self, group_id, artifact_id, version, file_type):
        """Construct the Maven URL based on groupId, artifactId, version, and file type (jar/pom)."""
        group_path = group_id.replace('.', '/')
        return f"{self.maven_base_url}{group_path}/{artifact_id}/{version}/{artifact_id}-{version}.{file_type}"

    def download_file(self, url, dest_folder):
        """Download a file from the given URL and save it to the destination folder."""
        response = requests.get(url)
        if response.status_code == 200:
            filename = url.split("/")[-1]
            file_path = os.path.join(dest_folder, filename)
            with open(file_path, "wb") as file:
                file.write(response.content)
            print(f"Downloaded {filename}")
            return file_path
        else:
            raise Exception(f"Failed to download {url}: {response.status_code}")

    def download_maven_artifact(self, group_id, artifact_id, version, dest_folder):
        """Download both the JAR and POM of a Maven artifact."""
        # Check if we've already downloaded this artifact
        artifact_key = f"{group_id}:{artifact_id}:{version}"
        if artifact_key in self.downloaded_artifacts:
            print(f"Artifact {artifact_key} already downloaded.")
            return

        self.downloaded_artifacts.add(artifact_key)

        # Download the JAR file
        jar_url = self.get_maven_url(group_id, artifact_id, version, "jar")
        jar_file = self.download_file(jar_url, dest_folder)

        # Download the POM file
        pom_url = self.get_maven_url(group_id, artifact_id, version, "pom")
        pom_file = self.download_file(pom_url, dest_folder)

        # Parse the POM and download dependencies
        properties = self.parse_pom_properties(pom_file)
        self.parse_pom_and_download_dependencies(pom_file, dest_folder, properties)

    def parse_pom_properties(self, pom_file, parent_properties=None):
        """Parse the POM file to extract properties and resolve them with parent properties."""
        tree = ET.parse(pom_file)
        root = tree.getroot()
        ns = {'mvn': 'http://maven.apache.org/POM/4.0.0'}

        # Initialize properties dictionary
        properties = parent_properties.copy() if parent_properties else {}

        # Extract properties from the POM
        properties_element = root.find('mvn:properties', namespaces=ns)
        if properties_element is not None:
            for prop in properties_element:
                properties[prop.tag.replace('{http://maven.apache.org/POM/4.0.0}', '')] = prop.text

        # Handle parent POMs
        parent_element = root.find('mvn:parent', namespaces=ns)
        if parent_element is not None:
            parent_group_id = parent_element.find('mvn:groupId', namespaces=ns).text
            parent_artifact_id = parent_element.find('mvn:artifactId', namespaces=ns).text
            parent_version = parent_element.find('mvn:version', namespaces=ns).text

            # Download parent POM
            parent_pom_url = self.get_maven_url(parent_group_id, parent_artifact_id, parent_version, "pom")
            parent_pom_file = self.download_file(parent_pom_url, os.path.dirname(pom_file))

            # Recursively parse parent POM properties
            parent_properties = self.parse_pom_properties(parent_pom_file, properties)

            # Merge parent properties
            properties.update(parent_properties)

        return properties

    def resolve_placeholders(self, text, properties):
        """Resolve placeholders in the text using the provided properties."""
        def replace_placeholder(match):
            placeholder = match.group(1)
            return properties.get(placeholder, match.group(0))  # Return the original if not found

        return re.sub(r'\$\{([^}]+)\}', replace_placeholder, text)

    def parse_pom_and_download_dependencies(self, pom_file, dest_folder, properties):
        """Parse the POM file to extract dependencies and download them."""
        tree = ET.parse(pom_file)
        root = tree.getroot()

        # Define the XML namespace for Maven POM files
        ns = {'mvn': 'http://maven.apache.org/POM/4.0.0'}

        # Find all dependencies in the POM
        dependencies = root.findall(".//mvn:dependency", namespaces=ns)
        for dep in dependencies:
            # Extract dependency details
            group_id_elem = dep.find("mvn:groupId", namespaces=ns)
            artifact_id_elem = dep.find("mvn:artifactId", namespaces=ns)
            version_elem = dep.find("mvn:version", namespaces=ns)

            # Resolve placeholders if necessary
            group_id = self.resolve_placeholders(group_id_elem.text, properties)
            artifact_id = self.resolve_placeholders(artifact_id_elem.text, properties)
            version = self.resolve_placeholders(version_elem.text, properties)

            # Skip if any essential information is missing
            if not group_id or not artifact_id or not version:
                print(f"Skipping dependency with missing information: {group_id}:{artifact_id}:{version}")
                continue

            print(f"Downloading dependency: {group_id}:{artifact_id}:{version}")

            try:
                # Recursively download the dependency
                self.download_maven_artifact(group_id, artifact_id, version, dest_folder)
            except Exception as e:
                print(f"Error downloading dependency {group_id}:{artifact_id}:{version}: {e}")
                continue  # Continue with other dependencies

    async def download_step(self, download: HyperloopDownload):
        download.status = DownloadStatus.DOWNLOADING
        await publish_status_update(self.rabbitmq, self.status_queue, download)
        # Download Maven artifact using the value of HyperloopDownload.dependency
        group_id, artifact_id, version = download.dependency.split(':')
        # Create a dedicated temp directory for the artifact
        sanitized_dependency = self.sanitize_filename(download.dependency)
        download_dir = os.path.join(self.temp_dir, sanitized_dependency)

        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        print(f"Step 1: Downloading Maven artifact {download.dependency}...")

        try:
            # Download the main artifact (JAR and POM)
            jar_file, pom_file = self.download_maven_artifact(group_id, artifact_id, version, download_dir)

            # Parse the POM and download all sub-dependencies
            self.parse_pom_and_download_dependencies(pom_file, download_dir)

            print(f"Maven artifact {download.dependency} downloaded successfully with dependencies.")
        except Exception as e:
            print(f"Error downloading Maven artifact {download.dependency}: {e}")
            download.status = DownloadStatus.FAILED
            await publish_status_update(self.rabbitmq, self.status_queue, download)
            return
        
        download.package_dir = download_dir


    async def packaging_step(self, download: HyperloopDownload):
        # Create a tarball for the Maven dependency
        sanitized_dependency = self.sanitize_filename(download.dependency)
        tarball_name = f"{sanitized_dependency}.tar"
        tarball_path = os.path.join(self.temp_dir, tarball_name)

        print(f"Step 2: Saving Maven artifact and dependencies to tarball {tarball_name}...")

        try:
            # Create a tarball of the artifact directory
            with tarfile.open(tarball_path, "w") as tarball:
                tarball.add(download.package_dir, arcname=os.path.basename(download.package_dir))
            print(f"Tarball created at {tarball_path}.")
        except Exception as e:
            print(f"Error saving Maven dependency to tarball: {e}")
            download.status = DownloadStatus.FAILED
            await publish_status_update(self.rabbitmq, self.status_queue, download)
            return

        # Attach the tarball name to the download object
        download.tarball_path = tarball_name

        # Set the status to SENDING
        download.status = DownloadStatus.SENDING
        await publish_status_update(self.rabbitmq, self.status_queue, download)

    async def sending_step(self, download: HyperloopDownload):
        # Use the TarballSender to send the tarball, passing both dependency and type
        tarball_path = download.tarball_path
        try:
            response = self.tarball_sender.send_tarball(tarball_path, download.dependency, download.type)
            if response.status_code == 200:
                download.status = DownloadStatus.DONE
            else:
                download.status = DownloadStatus.FAILED
        except Exception as e:
            download.status = DownloadStatus.FAILED

        # Publish the final status
        await publish_status_update(self.rabbitmq, self.status_queue, download)
    
    def cleanup_temp_files(self, download: HyperloopDownload):
        """Clean up the temporary files and directories after processing."""
        try:
            # Remove the download directory (contains the downloaded files)
            if hasattr(download, 'package_dir') and os.path.exists(download.package_dir):
                print(f"Cleaning up Maven package directory at {download.package_dir}")
                shutil.rmtree(download.package_dir)
            # Remove the tarball
            if hasattr(download, 'tarball_path') and os.path.exists(download.tarball_path):
                print(f"Removing tarball at {download.tarball_path}")
                os.remove(download.tarball_path)
        except Exception as e:
            print(f"Error during cleanup of temporary files: {e}")
