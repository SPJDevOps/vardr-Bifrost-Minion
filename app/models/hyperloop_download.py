from dataclasses import dataclass, field
from datetime import datetime

from app.models.download_status import DownloadStatus

@dataclass
class HyperloopDownload:
    id: int = 0  
    type: str = field(default_factory=str)
    dependency: str = field(default_factory=str)
    status: DownloadStatus = DownloadStatus.STARTED  # Default status is STARTED
    date: datetime = field(default_factory=datetime.now)  # Default is the current date/time

    # Custom method to serialize to dict (for JSON serialization)
    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "dependency": self.dependency,
            "status": self.status.value,  # Convert enum to string
            "date": self.date.isoformat()  # Convert datetime to string in ISO format
        }

    # Custom method to deserialize from a dict (for JSON deserialization)
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id", 0),
            type=data["type"],
            dependency=data["dependency"],
            status=DownloadStatus(data["status"]),  # Convert string back to enum
            date=datetime.fromisoformat(data["date"])  # Parse ISO formatted date string
        )