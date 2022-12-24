from dataclasses import dataclass

from telegram import Document, PhotoSize


@dataclass
class FileData:
    file_id: str
    file_name: str | None = None

    @staticmethod
    def from_telegram_object(obj: Document | PhotoSize) -> "FileData":
        if isinstance(obj, Document):
            return FileData(obj.file_id, obj.file_name)
        if isinstance(obj, PhotoSize):
            return FileData(obj.file_id)
        raise ValueError(f"Unknown Telegram object type: {type(obj)}")
