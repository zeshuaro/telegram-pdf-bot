from unittest.mock import MagicMock

import pytest

from pdf_bot.analytics import TaskType
from pdf_bot.pdf import PdfService
from pdf_bot.pdf_processor import EncryptPdfProcessor
from tests.file_task import FileTaskServiceTestMixin
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestEncryptPdfProcessor(
    FileTaskServiceTestMixin,
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    WAIT_PASSWORD_STATE = "wait_encrypt_password"
    WAIT_PASSWORD_TEXT = "Send me the password to encrypt your PDF file"
    FILE_PATH = "file_path"

    def setup_method(self) -> None:
        super().setup_method()
        self.pdf_service = MagicMock(spec=PdfService)
        self.file_task_service = self.mock_file_task_service()
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = EncryptPdfProcessor(
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
        assert actual == TaskType.encrypt_pdf

    @pytest.mark.asyncio
    async def test_process_file_task(self) -> None:
        self.pdf_service.encrypt_pdf.return_value.__aenter__.return_value = (
            self.FILE_PATH
        )

        async with self.sut.process_file_task(
            self.FILE_DATA, self.TELEGRAM_TEXT
        ) as actual:
            assert actual == self.FILE_PATH
            self.pdf_service.encrypt_pdf.assert_called_once_with(
                self.FILE_DATA.id, self.TELEGRAM_TEXT
            )
