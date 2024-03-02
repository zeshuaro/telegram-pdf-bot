from typing import Any

from pdf_bot.models import FileData


class FileDataTypeError(Exception):
    def __init__(self, file_data: FileData, *args: object) -> None:
        msg = f"Invalid file data type: {type(file_data)}"
        super().__init__(msg, *args)


class CallbackQueryDataTypeError(Exception):
    def __init__(self, data: Any, *args: object) -> None:
        msg = f"Invalid callback query data type: {type(data)}"
        super().__init__(msg, *args)


class UserIdError(Exception): ...
