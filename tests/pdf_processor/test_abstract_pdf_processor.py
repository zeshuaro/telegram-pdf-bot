from contextlib import contextmanager
from typing import Generator
from unittest.mock import MagicMock

from telegram.ext import ConversationHandler

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

    @contextmanager
    def process_file_task(
        self, _file_id: str, _message_text: str
    ) -> Generator[str, None, None]:
        yield "process_result"


class TestAbstractTelegramFileProcessor(
    FileTaskServiceTestMixin,
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    BACK = "Back"

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
        )

    def test_get_base_error_handlers(self) -> None:
        actual = self.sut.get_base_error_handlers()

        assert PdfServiceError in actual

        error = PdfServiceError("PDF error")
        handler = actual[type(error)]
        handler_result = handler(
            self.telegram_update,
            self.telegram_context,
            error,
            "file_id",
            "file_name",
        )

        assert handler_result == ConversationHandler.END
        self.telegram_update.effective_message.reply_text.assert_called_once_with(
            str(error)
        )
