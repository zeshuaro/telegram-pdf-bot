from unittest.mock import MagicMock

from telegram.ext import ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.pdf import PdfService
from pdf_bot.rename import RenameService
from tests.file_task import FileTaskServiceTestMixin
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestRenameService(
    FileTaskServiceTestMixin,
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    FILE_PATH = "file_path"
    WAIT_NEW_FILE_NAME = "wait_new_file_name"
    INVALID_CHARACTERS = r"\/*?:\'<>|"

    def setup_method(self) -> None:
        super().setup_method()
        self.pdf_service = MagicMock(spec=PdfService)
        self.file_task_service = self.mock_file_task_service()
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = RenameService(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

    def test_get_task_type(self) -> None:
        actual = self.sut.task_type
        assert actual == TaskType.rename_pdf

    def test_should_process_back_option(self) -> None:
        actual = self.sut.should_process_back_option
        assert actual is False

    def test_process_file_task(self) -> None:
        self.pdf_service.rename_pdf.return_value.__enter__.return_value = self.FILE_PATH

        with self.sut.process_file_task(
            self.telegram_document_id, self.telegram_text
        ) as actual:
            assert actual == self.FILE_PATH
            self.pdf_service.rename_pdf.assert_called_once_with(
                self.telegram_document_id, f"{self.telegram_text}.pdf"
            )

    def test_ask_new_file_name(self) -> None:
        actual = self.sut.ask_new_file_name(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_NEW_FILE_NAME
        self.telegram_service.reply_with_back_markup.assert_called_once()

    def test_rename_pdf(self) -> None:
        self.pdf_service.rename_pdf.return_value.__enter__.return_value = self.FILE_PATH

        actual = self.sut.rename_pdf(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.pdf_service.rename_pdf.assert_called_once_with(
            self.telegram_document_id, f"{self.telegram_text}.pdf"
        )

    def test_rename_pdf_invalid_file_name(self) -> None:
        self.telegram_message.text = "invalid/file?name"

        actual = self.sut.rename_pdf(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_NEW_FILE_NAME
        self.telegram_update.effective_message.reply_text.assert_called_once()
        self.pdf_service.rename_pdf.assert_not_called()

    def test_rename_pdf_with_back_option(self) -> None:
        self.telegram_message.text = "Back"

        actual = self.sut.rename_pdf(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_PDF_TASK
        self.pdf_service.rename_pdf.assert_not_called()
