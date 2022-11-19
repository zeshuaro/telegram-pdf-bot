from unittest.mock import MagicMock

import pytest
from telegram.ext import ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.pdf import PdfService
from pdf_bot.rotate import RotateService
from tests.file_task import FileTaskServiceTestMixin
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestRotateService(
    FileTaskServiceTestMixin,
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    FILE_PATH = "file_path"
    WAIT_ROTATE_DEGREE = "wait_rotate_degree"
    ROTATE_90 = "90"
    ROTATE_180 = "180"
    ROTATE_270 = "270"

    def setup_method(self) -> None:
        super().setup_method()
        self.pdf_service = MagicMock(spec=PdfService)
        self.file_task_service = self.mock_file_task_service()
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = RotateService(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

    def test_task_type(self) -> None:
        actual = self.sut.task_type
        assert actual == TaskType.rotate_pdf

    def test_should_process_back_option(self) -> None:
        actual = self.sut.should_process_back_option
        assert actual is False

    def test_process_file_task(self) -> None:
        self.pdf_service.rotate_pdf.return_value.__enter__.return_value = self.FILE_PATH

        with self.sut.process_file_task(
            self.telegram_document_id, self.ROTATE_90
        ) as actual:
            assert actual == self.FILE_PATH
            self.pdf_service.rotate_pdf.assert_called_once_with(
                self.telegram_document_id, int(self.ROTATE_90)
            )

    def test_ask_degree(self) -> None:
        actual = self.sut.ask_degree(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_ROTATE_DEGREE
        self.telegram_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.parametrize("degree", [ROTATE_90, ROTATE_180, ROTATE_270])
    def test_rotate_pdf(self, degree: str) -> None:
        self.telegram_message.text = degree
        self.pdf_service.rotate_pdf.return_value.__enter__.return_value = self.FILE_PATH

        actual = self.sut.rotate_pdf(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.pdf_service.rotate_pdf.assert_called_once_with(
            self.telegram_document_id, int(degree)
        )

    def test_rename_pdf_invalid_degree(self) -> None:
        self.telegram_message.text = "clearly_invalid"

        actual = self.sut.rotate_pdf(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_ROTATE_DEGREE
        self.telegram_update.effective_message.reply_text.assert_called_once()
        self.pdf_service.rotate_pdf.assert_not_called()

    def test_rotate_pdf_with_back_option(self) -> None:
        self.telegram_message.text = "Back"

        actual = self.sut.rotate_pdf(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_PDF_TASK
        self.pdf_service.rename_pdf.assert_not_called()
