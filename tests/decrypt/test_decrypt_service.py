from unittest.mock import MagicMock

from telegram.ext import ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import PDF_INFO
from pdf_bot.decrypt import DecryptService
from pdf_bot.pdf import PdfIncorrectPasswordError, PdfService
from pdf_bot.telegram import TelegramUserDataKeyError
from tests.file_task import FileTaskServiceTestMixin
from tests.language import LanguageServiceTestMixin
from tests.telegram import TelegramServiceTestMixin, TelegramTestMixin


class TestDecryptService(
    FileTaskServiceTestMixin,
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    WAIT_DECRYPT_PASSWORD = "wait_decrypt_password"
    FILE_PATH = "file_path"
    BACK = "Back"

    def setup_method(self) -> None:
        super().setup_method()
        self.pdf_service = MagicMock(spec=PdfService)
        self.file_task_service = self.mock_file_task_service()
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = DecryptService(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

    def test_ask_password(self) -> None:
        actual = self.sut.ask_password(self.telegram_update, self.telegram_context)
        assert actual == self.WAIT_DECRYPT_PASSWORD
        self.telegram_service.reply_with_back_markup.assert_called_once()

    def test_decrypt_pdf(self) -> None:
        self.pdf_service.decrypt_pdf.return_value.__enter__.return_value = (
            self.FILE_PATH
        )

        actual = self.sut.decrypt_pdf(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, PDF_INFO
        )
        self.pdf_service.decrypt_pdf.assert_called_once_with(
            self.telegram_document_id, self.telegram_text
        )
        self.telegram_service.reply_with_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            self.FILE_PATH,
            TaskType.decrypt_pdf,
        )

    def test_decrypt_pdf_incorrect_password(self) -> None:
        self.pdf_service.decrypt_pdf.side_effect = PdfIncorrectPasswordError()

        actual = self.sut.decrypt_pdf(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_DECRYPT_PASSWORD
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, PDF_INFO
        )
        self.pdf_service.decrypt_pdf.assert_called_once_with(
            self.telegram_document_id, self.telegram_text
        )
        self.telegram_context.user_data.__setitem__.assert_called_once_with(
            PDF_INFO, (self.telegram_document_id, self.telegram_document_name)
        )
        self.telegram_service.reply_with_file.assert_not_called()

    def test_decrypt_pdf_invalid_user_data(self) -> None:
        self.telegram_service.get_user_data.side_effect = TelegramUserDataKeyError()

        actual = self.sut.decrypt_pdf(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, PDF_INFO
        )
        self.pdf_service.decrypt_pdf.assert_not_called()
        self.telegram_service.reply_with_file.assert_not_called()

    def test_decrypt_pdf_back(self) -> None:
        self.telegram_message.text = self.BACK

        actual = self.sut.decrypt_pdf(self.telegram_update, self.telegram_context)

        assert actual == FileTaskServiceTestMixin.WAIT_PDF_TASK
        self.telegram_service.get_user_data.assert_not_called()
        self.pdf_service.decrypt_pdf.assert_not_called()
        self.telegram_service.reply_with_file.assert_not_called()
