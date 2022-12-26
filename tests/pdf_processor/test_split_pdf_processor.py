from unittest.mock import MagicMock

import pytest
from telegram.ext import ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.pdf import PdfService
from pdf_bot.pdf_processor import SplitPdfProcessor
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
    WAIT_SPLIT_RANGE = "wait_split_range"

    def setup_method(self) -> None:
        super().setup_method()
        self.telegram_update.callback_query = None

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

    def test_should_process_back_option(self) -> None:
        actual = self.sut.should_process_back_option
        assert actual is False

    @pytest.mark.asyncio
    async def test_process_file_task(self) -> None:
        self.pdf_service.split_pdf.return_value.__aenter__.return_value = self.FILE_PATH

        async with self.sut.process_file_task(
            self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_TEXT
        ) as actual:
            assert actual == self.FILE_PATH
            self.pdf_service.split_pdf.assert_called_once_with(
                self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_TEXT
            )

    @pytest.mark.asyncio
    async def test_ask_split_range(self) -> None:
        actual = await self.sut.ask_split_range(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_SPLIT_RANGE
        self.telegram_service.reply_with_back_markup.assert_called_once()

    @pytest.mark.asyncio
    async def test_split_pdf(self) -> None:
        self.pdf_service.split_pdf.return_value.__aenter__.return_value = self.FILE_PATH

        actual = await self.sut.split_pdf(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.pdf_service.split_pdf.assert_called_once_with(
            self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_TEXT
        )

    @pytest.mark.asyncio
    async def test_split_pdf_invalid_split_range(self) -> None:
        self.pdf_service.split_range_valid.return_value = False

        actual = await self.sut.split_pdf(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_SPLIT_RANGE
        self.telegram_service.reply_with_back_markup.assert_called_once()
        self.pdf_service.split_pdf.assert_not_called()

    @pytest.mark.asyncio
    async def test_split_pdf_back_option(self) -> None:
        self.telegram_message.text = "Back"

        actual = await self.sut.split_pdf(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_PDF_TASK
        self.file_task_service.ask_pdf_task.assert_called_once()
        self.pdf_service.split_pdf.assert_not_called()
