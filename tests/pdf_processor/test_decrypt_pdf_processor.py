from unittest.mock import MagicMock

import pytest

from pdf_bot.analytics import TaskType
from pdf_bot.models import FileData, TaskData
from pdf_bot.pdf import PdfIncorrectPasswordError, PdfService
from pdf_bot.pdf_processor import DecryptPdfData, DecryptPdfProcessor
from tests.file_task import FileTaskServiceTestMixin
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestDecryptPdfProcessor(
    FileTaskServiceTestMixin,
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    FILE_PATH = "file_path"
    WAIT_TEXT_INPUT = "wait_text_input"

    def setup_method(self) -> None:
        super().setup_method()
        self.pdf_service = MagicMock(spec=PdfService)
        self.file_task_service = self.mock_file_task_service()
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = DecryptPdfProcessor(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
            bypass_init_check=True,
        )

    def test_get_task_type(self) -> None:
        actual = self.sut.task_type
        assert actual == TaskType.decrypt_pdf

    def test_entry_point_data_type(self) -> None:
        actual = self.sut.entry_point_data_type
        assert actual == DecryptPdfData

    def test_should_process_back_option(self) -> None:
        actual = self.sut.should_process_back_option
        assert actual is False

    def test_task_data(self) -> None:
        actual = self.sut.task_data
        assert actual == TaskData("Decrypt", DecryptPdfData)

    def test_get_cleaned_text_input(self) -> None:
        actual = self.sut.get_cleaned_text_input(self.TELEGRAM_TEXT)
        assert actual == self.TELEGRAM_TEXT

    @pytest.mark.asyncio
    async def test_get_custom_error_handlers(self) -> None:
        file_data = FileData(self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_DOCUMENT_NAME)
        handlers = self.sut.custom_error_handlers

        handler = handlers.get(PdfIncorrectPasswordError)
        assert handler is not None

        actual = await handler(
            self.telegram_update, self.telegram_context, RuntimeError(), file_data
        )

        assert actual == self.WAIT_TEXT_INPUT
        self.telegram_message.reply_text.assert_called_once()
        self.telegram_service.cache_file_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_file_task(self) -> None:
        self.pdf_service.decrypt_pdf.return_value.__aenter__.return_value = (
            self.FILE_PATH
        )

        async with self.sut.process_file_task(
            self.TEXT_INPUT_DATA, self.TELEGRAM_TEXT
        ) as actual:
            assert actual == self.FILE_PATH
            self.pdf_service.decrypt_pdf.assert_called_once_with(
                self.TEXT_INPUT_DATA.id, self.TEXT_INPUT_DATA.text
            )

    @pytest.mark.asyncio
    async def test_process_file_task_invalid_file_data(self) -> None:
        with pytest.raises(TypeError):
            async with self.sut.process_file_task(self.FILE_DATA, self.TELEGRAM_TEXT):
                self.pdf_service.decrypt_pdf.assert_not_called()
