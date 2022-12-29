from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator

from telegram.ext import BaseHandler, CallbackQueryHandler

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, TaskData

from .abstract_pdf_processor import AbstractPdfProcessor


class ExtractPdfTextData(FileData):
    pass


class ExtractPdfTextProcessor(AbstractPdfProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.get_pdf_text

    @property
    def task_data(self) -> TaskData | None:
        return TaskData(_("Extract text"), ExtractPdfTextData)

    @property
    def handler(self) -> BaseHandler | None:
        return CallbackQueryHandler(self.process_file, pattern=ExtractPdfTextData)

    @asynccontextmanager
    async def process_file_task(
        self, file_data: FileData, _message_text: str
    ) -> AsyncGenerator[str, None]:
        async with self.pdf_service.extract_text_from_pdf(file_data.id) as path:
            yield path
