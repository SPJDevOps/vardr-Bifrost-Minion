import os
import asyncio
from app.processors.base_processor import BaseProcessor
from app.models.exceptions import DependencyNotFoundError, InternalError


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
            # Use asyncio.create_subprocess_exec for non-blocking subprocess calls
            process = await asyncio.create_subprocess_exec(
                "mvn",
                "dependency:get",
                "-Dartifact=" + dependency,
                "-Dmaven.repo.local=" + download_dir,
                "-DincludeScope=runtime",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                stderr_text = stderr.decode()
                # Check if it's a "not found" error
                if "Could not find artifact" in stderr_text or "not found" in stderr_text.lower():
                    raise DependencyNotFoundError(f"Maven artifact {dependency} does not exist")
                else:
                    raise InternalError(f"Maven download error: {stderr_text}")

            download.package_dir = download_dir
            
        except asyncio.TimeoutError:
            raise InternalError(f"Maven download timeout for {dependency}")
        except Exception as e:
            if isinstance(e, (DependencyNotFoundError, InternalError)):
                raise
            raise InternalError(f"Maven download error: {str(e)}") 