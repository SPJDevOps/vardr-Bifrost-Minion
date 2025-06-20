import os
import tarfile
from abc import ABC, abstractmethod
from faststream.rabbit import RabbitBroker
from app.helpers.nifi_uploader import NiFiUploader
from app.models.download_status import DownloadStatus
from app.models.hyperloop_download import HyperloopDownload
from app.processors.download_router import DependencyNotFoundError, InternalError


class BaseProcessor(ABC):
    """Base class for all download processors with common functionality"""
    
    def __init__(self, broker: RabbitBroker, status_queue: str, temp_dir: str):
        self.broker = broker
        self.status_queue = status_queue
        self.temp_dir = temp_dir
        self.tarball_sender = NiFiUploader()
        
        # Ensure the temp directory exists
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    async def process(self, download: HyperloopDownload):
        """Main processing pipeline - same for all processors"""
        try:
            await self.download_step(download)
            if download.status == DownloadStatus.FAILED:
                return
            
            await self.packaging_step(download)
            if download.status == DownloadStatus.FAILED:
                return
            
            await self.sending_step(download)
            
        finally:
            # Always cleanup, even if there was an error
            self.cleanup_temp_files(download)

    async def download_step(self, download: HyperloopDownload):
        """Download step with common error handling"""
        download.status = DownloadStatus.DOWNLOADING
        await self.publish_status_update(download)
        
        try:
            await self._download_dependency(download)
        except DependencyNotFoundError:
            # Re-raise dependency not found errors
            raise
        except Exception as e:
            # Convert other errors to internal errors for retry
            download.status = DownloadStatus.FAILED
            await self.publish_status_update(download)
            raise InternalError(f"Download error: {str(e)}")

    async def packaging_step(self, download: HyperloopDownload):
        """Packaging step with common error handling"""
        download.status = DownloadStatus.SENDING
        await self.publish_status_update(download)
        
        try:
            tarball_path = await self._create_tarball(download)
            download.tarball_path = tarball_path
        except Exception as e:
            download.status = DownloadStatus.FAILED
            await self.publish_status_update(download)
            raise InternalError(f"Packaging error: {str(e)}")

    async def sending_step(self, download: HyperloopDownload):
        """Sending step with common error handling"""
        try:
            response = self.tarball_sender.send_tarball(download.tarball_path, download)
            if response.status_code == 200:
                download.status = DownloadStatus.DONE
            else:
                download.status = DownloadStatus.FAILED
                raise InternalError(f"NiFi upload failed with status code: {response.status_code}")
        except Exception as e:
            download.status = DownloadStatus.FAILED
            raise InternalError(f"Sending error: {str(e)}")
        finally:
            await self.publish_status_update(download)

    async def _create_tarball(self, download: HyperloopDownload) -> str:
        """Create a tarball from the downloaded content"""
        sanitized_name = self.sanitize_filename(download.dependency)
        tarball_name = f"{sanitized_name}.tar"
        tarball_path = os.path.join(self.temp_dir, tarball_name)
        
        print(f"Creating tarball for {download.type} dependency...")
        
        with tarfile.open(tarball_path, "w") as tarball:
            if hasattr(download, 'package_dir') and os.path.exists(download.package_dir):
                # Directory-based content
                tarball.add(download.package_dir, arcname=os.path.basename(download.package_dir))
            elif hasattr(download, 'file_path') and os.path.exists(download.file_path):
                # Single file content
                tarball.add(download.file_path, arcname=os.path.basename(download.file_path))
            else:
                raise InternalError("No content to package into tarball")
        
        print(f"Tarball created at {tarball_path}")
        return tarball_path

    def cleanup_temp_files(self, download: HyperloopDownload):
        """Clean up temporary files and directories"""
        try:
            # Clean up package directory
            if hasattr(download, 'package_dir') and os.path.exists(download.package_dir):
                print(f"Cleaning up package directory at {download.package_dir}")
                import shutil
                shutil.rmtree(download.package_dir)
            
            # Clean up single file
            if hasattr(download, 'file_path') and os.path.exists(download.file_path):
                print(f"Cleaning up file at {download.file_path}")
                os.remove(download.file_path)
            
            # Clean up tarball
            if hasattr(download, 'tarball_path') and os.path.exists(download.tarball_path):
                print(f"Removing tarball at {download.tarball_path}")
                os.remove(download.tarball_path)
                
        except Exception as e:
            print(f"Error during cleanup: {e}")

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file saving"""
        return filename.replace("/", "_").replace(":", "_").replace(".", "_")

    async def publish_status_update(self, download: HyperloopDownload):
        """Publish status updates using FastStream broker"""
        await self.broker.publish(
            download.to_dict(),
            queue=self.status_queue
        )

    @abstractmethod
    async def _download_dependency(self, download: HyperloopDownload):
        """Abstract method that each processor must implement for its specific download logic"""
        pass 