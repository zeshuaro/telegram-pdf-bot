from contextlib import asynccontextmanager
from typing import AsyncGenerator

from pdf_bot.analytics import TaskType

from .abstract_pdf_processor import AbstractPDFProcessor


class ExtractPDFTextProcessor(AbstractPDFProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.get_pdf_text

    @property
    def should_process_back_option(self) -> bool:
        return False

    @asynccontextmanager
    async def process_file_task(
        self, file_id: str, _message_text: str
    ) -> AsyncGenerator[str, None]:
        async with self.pdf_service.extract_text_from_pdf(file_id) as path:
            yield path
