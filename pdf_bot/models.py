from dataclasses import dataclass

from telegram import Document, Message, PhotoSize


class BackData:
    ...


class SupportData:
    ...


@dataclass
class FileData:
    id: str  # noqa: A003
    name: str | None = None

    @classmethod
    def from_telegram_object(cls, obj: Document | PhotoSize) -> "FileData":
        if isinstance(obj, Document):
            return cls(obj.file_id, obj.file_name)
        if isinstance(obj, PhotoSize):
            return cls(obj.file_id)
        raise ValueError(f"Unknown Telegram object type: {type(obj)}")


@dataclass
class TaskData:
    label: str
    data_type: type[FileData]

    def get_file_data(self, obj: Document | PhotoSize) -> FileData:
        return self.data_type.from_telegram_object(obj)


@dataclass
class MessageData:
    chat_id: int | str
    message_id: int

    @classmethod
    def from_telegram_message(cls, message: Message) -> "MessageData":
        return cls(message.chat_id, message.id)


@dataclass
class FileTaskResult:
    path: str
    message: str | None = None
