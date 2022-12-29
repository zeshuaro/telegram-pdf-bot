from unittest.mock import MagicMock

import pytest

from pdf_bot.analytics import TaskType
from pdf_bot.models import TaskData
from pdf_bot.pdf import PdfService
from pdf_bot.pdf_processor import RenamePdfData, RenamePdfProcessor
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestRenamePdfProcessor(
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    FILE_PATH = "file_path"

    def setup_method(self) -> None:
        super().setup_method()

        self.pdf_service = MagicMock(spec=PdfService)
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = RenamePdfProcessor(
            self.pdf_service,
            self.telegram_service,
            self.language_service,
            bypass_init_check=True,
        )

    def test_task_type(self) -> None:
        actual = self.sut.task_type
        assert actual == TaskType.rename_pdf

    def test_entry_point_data_type(self) -> None:
        actual = self.sut.entry_point_data_type
        assert actual == RenamePdfData

    def test_task_data(self) -> None:
        actual = self.sut.task_data
        assert actual == TaskData("Rename", RenamePdfData)

    def test_get_cleaned_text_input(self) -> None:
        text = "valid.pdf"
        actual = self.sut.get_cleaned_text_input(text)
        assert actual == text

    def test_get_cleaned_text_input_invalid(self) -> None:
        text = "in<va>lid.pdf"
        actual = self.sut.get_cleaned_text_input(text)
        assert actual is None

    @pytest.mark.asyncio
    async def test_process_file_task(self) -> None:
        self.pdf_service.rename_pdf.return_value.__aenter__.return_value = (
            self.FILE_PATH
        )

        async with self.sut.process_file_task(
            self.TEXT_INPUT_DATA, self.TELEGRAM_TEXT
        ) as actual:
            assert actual == self.FILE_PATH
            self.pdf_service.rename_pdf.assert_called_once_with(
                self.TEXT_INPUT_DATA.id, self.TEXT_INPUT_DATA.text
            )

    @pytest.mark.asyncio
    async def test_process_file_task_invalid_file_data(self) -> None:
        with pytest.raises(TypeError):
            async with self.sut.process_file_task(self.FILE_DATA, self.TELEGRAM_TEXT):
                self.pdf_service.rename_pdf.assert_not_called()
