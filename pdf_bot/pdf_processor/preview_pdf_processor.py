from contextlib import contextmanager
from typing import Generator

from pdf_bot.analytics import TaskType

from .abstract_pdf_processor import AbstractPDFProcessor


class PreviewPDFProcessor(AbstractPDFProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.preview_pdf

    @property
    def should_process_back_option(self) -> bool:
        return False

    @contextmanager
    def process_file_task(
        self, file_id: str, _message_text: str
    ) -> Generator[str, None, None]:
        with self.pdf_service.preview_pdf(file_id) as path:
            yield path
