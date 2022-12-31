from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator

from telegram.ext import CallbackQueryHandler

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, FileTaskResult, TaskData

from .abstract_pdf_processor import AbstractPdfProcessor


class ExtractPdfImageData(FileData):
    pass


class ExtractPdfImageProcessor(AbstractPdfProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.get_pdf_image

    @property
    def task_data(self) -> TaskData:
        return TaskData(_("Extract images"), ExtractPdfImageData)

    @property
    def handler(self) -> CallbackQueryHandler:
        return CallbackQueryHandler(self.process_file, pattern=ExtractPdfImageData)

    @asynccontextmanager
    async def process_file_task(self, file_data: FileData) -> AsyncGenerator[FileTaskResult, None]:
        async with self.pdf_service.extract_pdf_images(file_data.id) as path:
            yield FileTaskResult(path)
