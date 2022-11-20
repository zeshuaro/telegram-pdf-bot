from contextlib import contextmanager
from typing import Generator
from unittest.mock import MagicMock

from pdf_bot.analytics import TaskType
from pdf_bot.crypto import AbstractCryptoService
from pdf_bot.pdf import PdfService
from tests.file_task import FileTaskServiceTestMixin
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class MockAbstractCryptoService(AbstractCryptoService):
    STATE = "state"

    @property
    def wait_password_state(self) -> str:
        return self.STATE

    @property
    def wait_password_text(self) -> str:
        return "text"

    @property
    def task_type(self) -> TaskType:
        return TaskType.decrypt_pdf

    @contextmanager
    def process_file_task(
        self, _file_id: str, _password: str
    ) -> Generator[str, None, None]:
        yield "result"


class TestAbstractCryptoService(
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

        self.sut = MockAbstractCryptoService(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

    def test_should_process_back_option(self) -> None:
        actual = self.sut.should_process_back_option
        assert actual is True

    def test_ask_password(self) -> None:
        actual = self.sut.ask_password(self.telegram_update, self.telegram_context)
        assert actual == MockAbstractCryptoService.STATE
        self.telegram_service.reply_with_back_markup.assert_called_once()
