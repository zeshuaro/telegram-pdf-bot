from contextlib import asynccontextmanager
from typing import AsyncGenerator

from pdf_bot.analytics import TaskType

from .abstract_pdf_processor import AbstractPdfProcessor


class PreviewPdfProcessor(AbstractPdfProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.preview_pdf

    @property
    def should_process_back_option(self) -> bool:
        return False

    @asynccontextmanager
    async def process_file_task(
        self, file_id: str, _message_text: str
    ) -> AsyncGenerator[str, None]:
        async with self.pdf_service.preview_pdf(file_id) as path:
            yield path
