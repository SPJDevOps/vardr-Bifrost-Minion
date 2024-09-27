from enum import Enum

class DownloadStatus(Enum):
    STARTED = "STARTED"
    DOWNLOADING = "DOWNLOADING"
    SENDING = "SENDING"
    DONE = "DONE"
    FAILED = "FAILED"