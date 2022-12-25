from contextlib import asynccontextmanager
from typing import AsyncGenerator

from pdf_bot.analytics import TaskType

from .abstract_pdf_processor import AbstractPDFProcessor


class PDFToImageProcessor(AbstractPDFProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.pdf_to_image

    @property
    def should_process_back_option(self) -> bool:
        return False

    @asynccontextmanager
    async def process_file_task(
        self, file_id: str, _message_text: str
    ) -> AsyncGenerator[str, None]:
        async with self.pdf_service.convert_pdf_to_images(file_id) as path:
            yield path
