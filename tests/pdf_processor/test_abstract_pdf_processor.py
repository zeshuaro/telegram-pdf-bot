from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import MagicMock

from pdf_bot.analytics import TaskType
from pdf_bot.pdf import PdfService, PdfServiceError
from pdf_bot.pdf_processor import AbstractPDFProcessor
from tests.file_task import FileTaskServiceTestMixin
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class MockProcessor(AbstractPDFProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.decrypt_pdf

    @property
    def should_process_back_option(self) -> bool:
        return True

    @asynccontextmanager
    async def process_file_task(
        self, _file_id: str, _message_text: str
    ) -> AsyncGenerator[str, None]:
        yield "process_result"


class TestAbstractTelegramFileProcessor(
    FileTaskServiceTestMixin,
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    def setup_method(self) -> None:
        super().setup_method()
        self.pdf_service = MagicMock(spec=PdfService)
        self.file_task_service = self.mock_file_task_service()
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = MockProcessor(
            self.pdf_service,
            self.file_task_service,
            self.telegram_service,
            self.language_service,
            bypass_init_check=True,
        )

    def test_generic_error_types(self) -> None:
        actual = self.sut.generic_error_types
        assert actual == {PdfServiceError}
