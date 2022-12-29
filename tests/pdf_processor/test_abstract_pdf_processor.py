from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import MagicMock

from telegram.ext import BaseHandler

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, FileTaskResult, TaskData
from pdf_bot.pdf import PdfService, PdfServiceError
from pdf_bot.pdf_processor import AbstractPdfProcessor
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class MockProcessor(AbstractPdfProcessor):
    FILE_TASK_RESULT = FileTaskResult("path")

    @property
    def task_type(self) -> TaskType:
        return TaskType.decrypt_pdf

    @property
    def task_data(self) -> TaskData:
        return MagicMock(spec=TaskData)

    @property
    def handler(self) -> BaseHandler:
        return MagicMock(spec=BaseHandler)

    @asynccontextmanager
    async def process_file_task(
        self, _file_data: FileData
    ) -> AsyncGenerator[FileTaskResult, None]:
        yield self.FILE_TASK_RESULT


class TestAbstractPdfProcessor(
    LanguageServiceTestMixin, TelegramServiceTestMixin, TelegramTestMixin
):
    def setup_method(self) -> None:
        super().setup_method()
        self.pdf_service = MagicMock(spec=PdfService)
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = MockProcessor(
            self.pdf_service,
            self.telegram_service,
            self.language_service,
            bypass_init_check=True,
        )

    def test_generic_error_types(self) -> None:
        actual = self.sut.generic_error_types
        assert actual == {PdfServiceError}
