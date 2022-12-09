from contextlib import contextmanager
from typing import Generator

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData

from .abstract_image_processor import AbstractImageProcessor


class ImageToPDFProcessor(AbstractImageProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.image_to_pdf

    @property
    def should_process_back_option(self) -> bool:
        return False

    @contextmanager
    def process_file_task(
        self, file_id: str, _message_text: str
    ) -> Generator[str, None, None]:
        with self.image_service.convert_images_to_pdf([FileData(file_id)]) as path:
            yield path
