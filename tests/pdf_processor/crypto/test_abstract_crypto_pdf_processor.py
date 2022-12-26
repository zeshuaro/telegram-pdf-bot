from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import MagicMock

import pytest

from pdf_bot.analytics import TaskType
from pdf_bot.pdf import PdfService
from pdf_bot.pdf_processor import AbstractCryptoPDFProcessor
from tests.file_task import FileTaskServiceTestMixin
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class MockAbstractCryptoPDFProcessor(AbstractCryptoPDFProcessor):
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

    @asynccontextmanager
    async def process_file_task(
        self, _file_id: str, _password: str
    ) -> AsyncGenerator[str, None]:
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

        self.sut = MockAbstractCryptoPDFProcessor(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
            bypass_init_check=True,
        )

    def test_should_process_back_option(self) -> None:
        actual = self.sut.should_process_back_option
        assert actual is True

    @pytest.mark.asyncio
    async def test_ask_password(self) -> None:
        actual = await self.sut.ask_password(
            self.telegram_update, self.telegram_context
        )
        assert actual == MockAbstractCryptoPDFProcessor.STATE
        self.telegram_service.reply_with_back_markup.assert_called_once()
