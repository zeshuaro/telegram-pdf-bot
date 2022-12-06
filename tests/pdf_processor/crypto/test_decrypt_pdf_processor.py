from unittest.mock import MagicMock

from pdf_bot.analytics import TaskType
from pdf_bot.consts import PDF_INFO
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

    def test_get_custom_error_handlers(self) -> None:
        actual = self.sut.custom_error_handlers

        handler = actual.get(PdfIncorrectPasswordError)
        assert handler is not None

        actual = handler(
            self.telegram_update,
            self.telegram_context,
            RuntimeError(),
            self.telegram_document_id,
            self.telegram_document_name,
        )

        assert actual == self.WAIT_PASSWORD_STATE
        self.telegram_message.reply_text.assert_called_once()
        self.telegram_context.user_data.__setitem__.assert_called_once_with(
            PDF_INFO, (self.telegram_document_id, self.telegram_document_name)
        )

    def test_process_file_task(self) -> None:
        self.pdf_service.decrypt_pdf.return_value.__enter__.return_value = (
            self.FILE_PATH
        )

        with self.sut.process_file_task(
            self.telegram_document_id, self.telegram_text
        ) as actual:
            assert actual == self.FILE_PATH
            self.pdf_service.decrypt_pdf.assert_called_once_with(
                self.telegram_document_id, self.telegram_text
            )
