from unittest.mock import MagicMock

from pdf_diff import NoDifferenceError
from telegram.ext import ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.compare import CompareService
from pdf_bot.consts import BACK, CANCEL
from pdf_bot.pdf import PdfService
from pdf_bot.telegram_internal import TelegramServiceError, TelegramUserDataKeyError
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestCompareService(
    LanguageServiceTestMixin, TelegramServiceTestMixin, TelegramTestMixin
):
    FILE_PATH = "file_path"
    COMPARE_ID = "compare_id"
    WAIT_FIRST_PDF = 0
    WAIT_SECOND_PDF = 1

    def setup_method(self) -> None:
        super().setup_method()
        self.pdf_service = MagicMock(spec=PdfService)
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = CompareService(
            self.pdf_service, self.telegram_service, self.language_service
        )

    def test_ask_first_pdf(self) -> None:
        actual = self.sut.ask_first_pdf(self.telegram_update, self.telegram_context)
        assert actual == self.WAIT_FIRST_PDF
        self.telegram_update.effective_message.reply_text.assert_called_once()

    def test_check_first_pdf(self) -> None:
        actual = self.sut.check_first_pdf(self.telegram_update, self.telegram_context)
        assert actual == self.WAIT_SECOND_PDF
        self.telegram_context.user_data.__setitem__.assert_called_with(
            self.COMPARE_ID, self.TELEGRAM_DOCUMENT_ID
        )

    def test_check_first_pdf_invalid_pdf(self) -> None:
        self.telegram_service.check_pdf_document.side_effect = TelegramServiceError()

        actual = self.sut.check_first_pdf(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_FIRST_PDF
        self.telegram_context.user_data.__setitem__.assert_not_called()

    def test_compare_pdfs(self) -> None:
        self.telegram_service.get_user_data.return_value = self.TELEGRAM_DOCUMENT_ID
        self.pdf_service.compare_pdfs.return_value.__enter__.return_value = (
            self.FILE_PATH
        )

        actual = self.sut.compare_pdfs(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.pdf_service.compare_pdfs.assert_called_with(
            self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_DOCUMENT_ID
        )
        self.telegram_service.reply_with_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            self.FILE_PATH,
            TaskType.compare_pdf,
        )

    def test_compare_pdfs_no_differences(self) -> None:
        self.telegram_service.get_user_data.return_value = self.TELEGRAM_DOCUMENT_ID
        self.pdf_service.compare_pdfs.return_value.__enter__.side_effect = (
            NoDifferenceError()
        )

        actual = self.sut.compare_pdfs(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.pdf_service.compare_pdfs.assert_called_with(
            self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_DOCUMENT_ID
        )
        self.telegram_service.reply_with_file.assert_not_called()

    def test_compare_pdfs_invalid_user_data(self) -> None:
        self.telegram_service.get_user_data.side_effect = TelegramUserDataKeyError()

        actual = self.sut.compare_pdfs(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.pdf_service.compare_pdfs.assert_not_called()
        self.telegram_service.reply_with_file.assert_not_called()

    def test_compare_pdfs_invalid_pdf(self) -> None:
        self.telegram_service.check_pdf_document.side_effect = TelegramServiceError()

        actual = self.sut.compare_pdfs(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_SECOND_PDF
        self.pdf_service.compare_pdfs.assert_not_called()
        self.telegram_service.reply_with_file.assert_not_called()

    def test_check_text_back(self) -> None:
        self.telegram_message.text = BACK
        actual = self.sut.check_text(self.telegram_update, self.telegram_context)
        assert actual == self.WAIT_FIRST_PDF

    def test_check_text_cancel(self) -> None:
        self.telegram_service.cancel_conversation.return_value = ConversationHandler.END
        self.telegram_message.text = CANCEL

        actual = self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END

    def test_check_text_unknown(self) -> None:
        self.telegram_message.text = "clearly_unknown"
        actual = self.sut.check_text(self.telegram_update, self.telegram_context)
        assert actual is None
