from contextlib import asynccontextmanager
from typing import AsyncGenerator

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData

from .abstract_image_processor import AbstractImageProcessor


class BeautifyImageProcessor(AbstractImageProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.beautify_image

    @property
    def should_process_back_option(self) -> bool:
        return False

    @asynccontextmanager
    async def process_file_task(
        self, file_id: str, _message_text: str
    ) -> AsyncGenerator[str, None]:
        async with self.image_service.beautify_and_convert_images_to_pdf(
            [FileData(file_id)]
        ) as path:
            yield path
