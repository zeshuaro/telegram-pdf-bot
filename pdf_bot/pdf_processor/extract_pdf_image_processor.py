from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator

from telegram.ext import BaseHandler, CallbackQueryHandler

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, TaskData

from .abstract_pdf_processor import AbstractPdfProcessor


class ExtractPdfImageData(FileData):
    pass


class ExtractPdfImageProcessor(AbstractPdfProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.get_pdf_image

    @property
    def task_data(self) -> TaskData | None:
        return TaskData(_("Extract images"), ExtractPdfImageData)

    @property
    def should_process_back_option(self) -> bool:
        return False

    @property
    def handler(self) -> BaseHandler | None:
        return CallbackQueryHandler(self.process_file, pattern=ExtractPdfImageData)

    @asynccontextmanager
    async def process_file_task(
        self, file_id: str, _message_text: str
    ) -> AsyncGenerator[str, None]:
        async with self.pdf_service.extract_pdf_images(file_id) as path:
            yield path
