from contextlib import contextmanager
from typing import Generator

from pdf_bot.analytics import TaskType
from pdf_bot.file_processor import AbstractFileProcessor


class ExtractPDFImageProcessor(AbstractFileProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.get_pdf_image

    @property
    def should_process_back_option(self) -> bool:
        return False

    @contextmanager
    def process_file_task(
        self, file_id: str, _message_text: str
    ) -> Generator[str, None, None]:
        with self.pdf_service.extract_pdf_images(file_id) as path:
            yield path
