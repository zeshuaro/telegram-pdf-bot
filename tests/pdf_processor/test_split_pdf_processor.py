from unittest.mock import MagicMock

import pytest

from pdf_bot.analytics import TaskType
from pdf_bot.models import TaskData
from pdf_bot.pdf import PdfService
from pdf_bot.pdf_processor import SplitPdfData, SplitPdfProcessor
from tests.file_task import FileTaskServiceTestMixin
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestSplitPdfProcessor(
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

        self.sut = SplitPdfProcessor(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
            bypass_init_check=True,
        )

    def test_task_type(self) -> None:
        actual = self.sut.task_type
        assert actual == TaskType.split_pdf

    def test_entry_point_data_type(self) -> None:
        actual = self.sut.entry_point_data_type
        assert actual == SplitPdfData

    def test_should_process_back_option(self) -> None:
        actual = self.sut.should_process_back_option
        assert actual is False

    def test_task_data(self) -> None:
        actual = self.sut.task_data
        assert actual == TaskData("Split", SplitPdfData)

    @pytest.mark.parametrize(
        "is_valid,expected", [(True, TelegramTestMixin.TELEGRAM_TEXT), (False, None)]
    )
    def test_get_cleaned_text_input(self, is_valid: bool, expected: str | None) -> None:
        self.pdf_service.split_range_valid.return_value = is_valid
        actual = self.sut.get_cleaned_text_input(self.TELEGRAM_TEXT)
        assert actual == expected

    @pytest.mark.asyncio
    async def test_process_file_task(self) -> None:
        self.pdf_service.split_pdf.return_value.__aenter__.return_value = self.FILE_PATH

        async with self.sut.process_file_task(
            self.TEXT_INPUT_DATA, self.TELEGRAM_TEXT
        ) as actual:
            assert actual == self.FILE_PATH
            self.pdf_service.split_pdf.assert_called_once_with(
                self.TEXT_INPUT_DATA.id, self.TEXT_INPUT_DATA.text
            )

    @pytest.mark.asyncio
    async def test_process_file_task_invalid_file_data(self) -> None:
        with pytest.raises(TypeError):
            async with self.sut.process_file_task(self.FILE_DATA, self.TELEGRAM_TEXT):
                self.pdf_service.split_pdf.assert_not_called()
