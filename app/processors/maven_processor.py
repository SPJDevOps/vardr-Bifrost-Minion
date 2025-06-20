import os
import subprocess
from app.processors.base_processor import BaseProcessor
from app.processors.download_router import DependencyNotFoundError, InternalError


class MavenProcessor(BaseProcessor):
    def __init__(self, broker, status_queue):
        super().__init__(broker, status_queue, "/tmp/maven-packages/")

    async def _download_dependency(self, download):
        """Download Maven artifact and its dependencies"""
        dependency = download.dependency  # Maven coordinate, e.g., "group:artifact:version"
        
        # Validate Maven coordinate format
        if dependency.count(":") != 2:
            raise DependencyNotFoundError(f"Invalid Maven coordinate format: {dependency}. Expected format: group:artifact:version")
        
        group_id, artifact_id, version = dependency.split(":")
        
        # Create a directory for this artifact
        download_dir = os.path.join(self.temp_dir, self.sanitize_filename(dependency))
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        print(f"Downloading Maven artifact and dependencies for {dependency}...")

        try:
            result = subprocess.run(
                [
                    "mvn",
                    "dependency:get",
                    "-Dartifact=" + dependency,
                    "-Dmaven.repo.local=" + download_dir,
                    "-DincludeScope=runtime",
                ],
                check=True,
                capture_output=True,
                text=True
            )

            download.package_dir = download_dir
            
        except subprocess.CalledProcessError as e:
            # Check if it's a "not found" error
            if "Could not find artifact" in e.stderr or "not found" in e.stderr.lower():
                raise DependencyNotFoundError(f"Maven artifact {dependency} does not exist")
            else:
                raise InternalError(f"Maven download error: {e.stderr}") 