from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator, Callable

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, FileTaskResult, TaskData

from .abstract_pdf_text_input_processor import AbstractPdfTextInputProcessor, TextInputData


class EncryptPdfData(FileData):
    pass


class EncryptPdfProcessor(AbstractPdfTextInputProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.encrypt_pdf

    @property
    def entry_point_data_type(self) -> type[EncryptPdfData]:
        return EncryptPdfData

    @property
    def task_data(self) -> TaskData:
        return TaskData(_("Encrypt"), self.entry_point_data_type)

    @property
    def invalid_text_input_error(self) -> str:  # pragma: no cover
        return ""

    def get_ask_text_input_text(self, _: Callable[[str], str]) -> str:  # pragma: no cover
        return _("Send me the password to encrypt your PDF file")

    def get_cleaned_text_input(self, text: str) -> str:
        return text

    @asynccontextmanager
    async def process_file_task(self, file_data: FileData) -> AsyncGenerator[FileTaskResult, None]:
        if not isinstance(file_data, TextInputData):
            raise TypeError(f"Invalid file data: {type(file_data)}")

        async with self.pdf_service.encrypt_pdf(file_data.id, file_data.text) as path:
            yield FileTaskResult(path)
