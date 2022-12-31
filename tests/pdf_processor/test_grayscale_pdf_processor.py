from unittest.mock import MagicMock

import pytest
from telegram.ext import CallbackQueryHandler

from pdf_bot.analytics import TaskType
from pdf_bot.models import TaskData
from pdf_bot.pdf import PdfService
from pdf_bot.pdf_processor import GrayscalePdfData, GrayscalePdfProcessor
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestGrayscalePdfProcessor(
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    def setup_method(self) -> None:
        super().setup_method()
        self.pdf_service = MagicMock(spec=PdfService)
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = GrayscalePdfProcessor(
            self.pdf_service,
            self.telegram_service,
            self.language_service,
            bypass_init_check=True,
        )

    def test_get_task_type(self) -> None:
        actual = self.sut.task_type
        assert actual == TaskType.grayscale_pdf

    def test_task_data(self) -> None:
        actual = self.sut.task_data
        assert actual == TaskData("Grayscale", GrayscalePdfData)

    def test_handler(self) -> None:
        actual = self.sut.handler

        assert isinstance(actual, CallbackQueryHandler)
        assert actual.pattern == GrayscalePdfData

    @pytest.mark.asyncio
    async def test_process_file_task(self) -> None:
        self.pdf_service.grayscale_pdf.return_value.__aenter__.return_value = self.FILE_PATH

        async with self.sut.process_file_task(self.FILE_DATA) as actual:
            assert actual == self.FILE_TASK_RESULT
            self.pdf_service.grayscale_pdf.assert_called_once_with(self.FILE_DATA.id)
