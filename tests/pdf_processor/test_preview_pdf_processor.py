from unittest.mock import MagicMock

from pdf_bot.analytics import TaskType
from pdf_bot.pdf import PdfService
from pdf_bot.pdf_processor import PreviewPDFProcessor
from tests.file_task import FileTaskServiceTestMixin
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestPreviewPDFProcessor(
    FileTaskServiceTestMixin,
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    FILE_PATH = "file_path"

    def setup_method(self) -> None:
        super().setup_method()
        self.pdf_service = MagicMock(spec=PdfService)
        self.file_task_service = self.mock_file_task_service()
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = PreviewPDFProcessor(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

    def test_get_task_type(self) -> None:
        actual = self.sut.task_type
        assert actual == TaskType.preview_pdf

    def test_should_process_back_option(self) -> None:
        actual = self.sut.should_process_back_option
        assert actual is False

    def test_process_file_task(self) -> None:
        self.pdf_service.preview_pdf.return_value.__enter__.return_value = (
            self.FILE_PATH
        )

        with self.sut.process_file_task(
            self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_TEXT
        ) as actual:
            assert actual == self.FILE_PATH
            self.pdf_service.preview_pdf.assert_called_once_with(
                self.TELEGRAM_DOCUMENT_ID
            )
