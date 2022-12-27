from contextlib import asynccontextmanager
from typing import AsyncGenerator

from telegram.ext import BaseHandler, CallbackQueryHandler

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, TaskData

from .abstract_pdf_processor import AbstractPdfProcessor


class OcrPdfData(FileData):
    pass


class OcrPdfProcessor(AbstractPdfProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.ocr_pdf

    @property
    def task_data(self) -> TaskData | None:
        return TaskData("OCR", OcrPdfData)

    @property
    def should_process_back_option(self) -> bool:
        return False

    @property
    def handler(self) -> BaseHandler | None:
        return CallbackQueryHandler(self.process_file, pattern=OcrPdfData)

    @asynccontextmanager
    async def process_file_task(
        self, file_data: FileData, _message_text: str
    ) -> AsyncGenerator[str, None]:
        async with self.pdf_service.ocr_pdf(file_data.id) as path:
            yield path
