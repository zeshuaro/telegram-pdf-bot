from dataclasses import dataclass

from telegram import Document


@dataclass
class FileData:
    id: str
    name: str

    @staticmethod
    def from_telegram_document(document: Document) -> "FileData":
        return FileData(document.file_id, document.file_name)
