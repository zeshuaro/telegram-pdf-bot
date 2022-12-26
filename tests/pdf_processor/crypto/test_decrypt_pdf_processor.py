from unittest.mock import MagicMock

import pytest

from pdf_bot.analytics import TaskType
from pdf_bot.consts import FILE_DATA
from pdf_bot.pdf import PdfIncorrectPasswordError, PdfService
from pdf_bot.pdf_processor import DecryptPDFProcessor
from tests.file_task import FileTaskServiceTestMixin
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestDecryptPDFProcessor(
    FileTaskServiceTestMixin,
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    WAIT_PASSWORD_STATE = "wait_decrypt_password"
    WAIT_PASSWORD_TEXT = "Send me the password to decrypt your PDF file"
    FILE_PATH = "file_path"

    def setup_method(self) -> None:
        super().setup_method()
        self.pdf_service = MagicMock(spec=PdfService)
        self.file_task_service = self.mock_file_task_service()
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = DecryptPDFProcessor(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
            bypass_init_check=True,
        )

    def test_get_wait_password_state(self) -> None:
        actual = self.sut.wait_password_state
        assert actual == self.WAIT_PASSWORD_STATE

    def test_get_wait_password_text(self) -> None:
        actual = self.sut.wait_password_text
        assert actual == self.WAIT_PASSWORD_TEXT

    def test_get_task_type(self) -> None:
        actual = self.sut.task_type
        assert actual == TaskType.decrypt_pdf

    @pytest.mark.asyncio
    async def test_get_custom_error_handlers(self) -> None:
        handlers = self.sut.custom_error_handlers

        handler = handlers.get(PdfIncorrectPasswordError)
        assert handler is not None

        actual = await handler(
            self.telegram_update,
            self.telegram_context,
            RuntimeError(),
            self.TELEGRAM_DOCUMENT_ID,
            self.TELEGRAM_DOCUMENT_NAME,
        )

        assert actual == self.WAIT_PASSWORD_STATE
        self.telegram_message.reply_text.assert_called_once()
        self.telegram_context.user_data.__setitem__.assert_called_once_with(
            FILE_DATA, (self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_DOCUMENT_NAME)
        )

    @pytest.mark.asyncio
    async def test_process_file_task(self) -> None:
        self.pdf_service.decrypt_pdf.return_value.__aenter__.return_value = (
            self.FILE_PATH
        )

        async with self.sut.process_file_task(
            self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_TEXT
        ) as actual:
            assert actual == self.FILE_PATH
            self.pdf_service.decrypt_pdf.assert_called_once_with(
                self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_TEXT
            )
