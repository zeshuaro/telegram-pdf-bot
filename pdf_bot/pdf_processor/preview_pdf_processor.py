from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator

from telegram.ext import CallbackQueryHandler

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, TaskData

from .abstract_pdf_processor import AbstractPdfProcessor


class PreviewPdfData(FileData):
    pass


class PreviewPdfProcessor(AbstractPdfProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.preview_pdf

    @property
    def task_data(self) -> TaskData:
        return TaskData(_("Preview"), PreviewPdfData)

    @property
    def handler(self) -> CallbackQueryHandler:
        return CallbackQueryHandler(self.process_file, pattern=PreviewPdfData)

    @asynccontextmanager
    async def process_file_task(
        self, file_data: FileData, _message_text: str
    ) -> AsyncGenerator[str, None]:
        async with self.pdf_service.preview_pdf(file_data.id) as path:
            yield path
