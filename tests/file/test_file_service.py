from unittest.mock import MagicMock

from telegram.ext import ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.file import FileService
from pdf_bot.pdf import PdfService
from pdf_bot.pdf.models import CompressResult
from pdf_bot.telegram_internal import TelegramServiceError
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestDecryptService(
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    FILE_PATH = "file_path"
    COMPRESS_RESULT = CompressResult(2, 1, FILE_PATH)

    def setup_method(self) -> None:
        super().setup_method()
        self.pdf_service = MagicMock(spec=PdfService)
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = FileService(
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

    def test_compress_pdf(self) -> None:
        self.pdf_service.compress_pdf.return_value.__enter__.return_value = (
            self.COMPRESS_RESULT
        )

        actual = self.sut.compress_pdf(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_update.effective_message.reply_text.assert_called_once()
        self.pdf_service.compress_pdf.assert_called_once_with(self.telegram_document_id)
        self.telegram_service.reply_with_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            self.FILE_PATH,
            TaskType.compress_pdf,
        )

    def test_compress_pdf_invalid_user_data(self) -> None:
        self.telegram_service.get_user_data.side_effect = TelegramServiceError()

        actual = self.sut.compress_pdf(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_update.effective_message.reply_text.assert_called_once()
        self.pdf_service.compress_pdf.assert_not_called()
        self.telegram_service.reply_with_file.assert_not_called()
