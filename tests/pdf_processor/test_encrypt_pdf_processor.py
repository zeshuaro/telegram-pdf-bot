from unittest.mock import MagicMock

import pytest

from pdf_bot.analytics import TaskType
from pdf_bot.models import TaskData
from pdf_bot.pdf import PdfService
from pdf_bot.pdf_processor import EncryptPdfData, EncryptPdfProcessor
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestEncryptPdfProcessor(
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    def setup_method(self) -> None:
        super().setup_method()
        self.pdf_service = MagicMock(spec=PdfService)
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = EncryptPdfProcessor(
            self.pdf_service,
            self.telegram_service,
            self.language_service,
            bypass_init_check=True,
        )

    def test_get_task_type(self) -> None:
        actual = self.sut.task_type
        assert actual == TaskType.encrypt_pdf

    def test_entry_point_data_type(self) -> None:
        actual = self.sut.entry_point_data_type
        assert actual == EncryptPdfData

    def test_task_data(self) -> None:
        actual = self.sut.task_data
        assert actual == TaskData("Encrypt", EncryptPdfData)

    def test_get_cleaned_text_input(self) -> None:
        actual = self.sut.get_cleaned_text_input(self.TELEGRAM_TEXT)
        assert actual == self.TELEGRAM_TEXT

    @pytest.mark.asyncio
    async def test_process_file_task(self) -> None:
        self.pdf_service.encrypt_pdf.return_value.__aenter__.return_value = self.FILE_PATH

        async with self.sut.process_file_task(self.TEXT_INPUT_DATA) as actual:
            assert actual == self.FILE_TASK_RESULT
            self.pdf_service.encrypt_pdf.assert_called_once_with(
                self.TEXT_INPUT_DATA.id, self.TEXT_INPUT_DATA.text
            )

    @pytest.mark.asyncio
    async def test_process_file_task_invalid_file_data(self) -> None:
        with pytest.raises(TypeError):
            async with self.sut.process_file_task(self.FILE_DATA):
                pass
        self.pdf_service.encrypt_pdf.assert_not_called()
