from unittest.mock import MagicMock

from pdf_bot.analytics import TaskType
from pdf_bot.crypto import EncryptService
from pdf_bot.pdf import PdfService
from tests.file_task import FileTaskServiceTestMixin
from tests.language import LanguageServiceTestMixin
from tests.telegram import TelegramServiceTestMixin, TelegramTestMixin


class TestDecryptService(
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

        self.sut = EncryptService(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
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

    def test_process_file_task(self) -> None:
        self.pdf_service.encrypt_pdf.return_value.__enter__.return_value = (
            self.FILE_PATH
        )

        with self.sut.process_file_task(
            self.telegram_document_id, self.telegram_text
        ) as actual:
            assert actual == self.FILE_PATH
            self.pdf_service.encrypt_pdf.assert_called_once_with(
                self.telegram_document_id, self.telegram_text
            )
