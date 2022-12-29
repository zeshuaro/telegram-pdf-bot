from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator

from telegram.ext import CallbackQueryHandler

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, FileTaskResult, TaskData

from .abstract_pdf_processor import AbstractPdfProcessor


class PdfToImageData(FileData):
    pass


class PdfToImageProcessor(AbstractPdfProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.pdf_to_image

    @property
    def task_data(self) -> TaskData:
        return TaskData(_("To images"), PdfToImageData)

    @property
    def handler(self) -> CallbackQueryHandler:
        return CallbackQueryHandler(self.process_file, pattern=PdfToImageData)

    @asynccontextmanager
    async def process_file_task(
        self, file_data: FileData
    ) -> AsyncGenerator[FileTaskResult, None]:
        async with self.pdf_service.convert_pdf_to_images(file_data.id) as path:
            yield FileTaskResult(path)
