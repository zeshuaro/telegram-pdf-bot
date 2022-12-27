from unittest.mock import MagicMock

import pytest
from telegram.ext import ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.pdf import PdfService
from pdf_bot.pdf.models import ScaleData
from pdf_bot.pdf_processor import ScalePdfProcessor
from tests.file_task import FileTaskServiceTestMixin
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestPdfProcessor(
    FileTaskServiceTestMixin,
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    FILE_PATH = "file_path"
    BY_SCALING_FACTOR = "By scaling factor"
    TO_DIMENSION = "To dimension"
    WAIT_SCALE_TYPE = "wait_scale_type"
    WAIT_SCALE_FACTOR = "wait_scale_factor"
    WAIT_SCALE_DIMENSION = "wait_scale_dimension"
    SCALE_DATA_TEXT = "0.1 0.2"
    SCALE_DATA = ScaleData(0.1, 0.2)

    def setup_method(self) -> None:
        super().setup_method()
        self.telegram_update.callback_query = None

        self.pdf_service = MagicMock(spec=PdfService)
        self.file_task_service = self.mock_file_task_service()
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = ScalePdfProcessor(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
            bypass_init_check=True,
        )

    def test_task_type(self) -> None:
        actual = self.sut.task_type
        assert actual == TaskType.scale_pdf

    def test_should_process_back_option(self) -> None:
        actual = self.sut.should_process_back_option
        assert actual is False

    @pytest.mark.asyncio
    async def test_process_file_task(self) -> None:
        self.pdf_service.scale_pdf.return_value.__aenter__.return_value = self.FILE_PATH

        async with self.sut.process_file_task(
            self.FILE_DATA, self.SCALE_DATA_TEXT
        ) as actual:
            assert actual == self.FILE_PATH
            self.pdf_service.scale_pdf.assert_called_once_with(
                self.FILE_DATA.id, self.SCALE_DATA
            )

    @pytest.mark.asyncio
    async def test_ask_scale_type(self) -> None:
        actual = await self.sut.ask_scale_type(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_SCALE_TYPE
        self.telegram_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.parametrize(
        "scale_text,scale_state",
        [(BY_SCALING_FACTOR, WAIT_SCALE_FACTOR), (TO_DIMENSION, WAIT_SCALE_DIMENSION)],
    )
    @pytest.mark.asyncio
    async def test_check_scale_type_by_factor(
        self, scale_text: str, scale_state: str
    ) -> None:
        self.telegram_message.text = scale_text

        actual = await self.sut.check_scale_type(
            self.telegram_update, self.telegram_context
        )

        assert actual == scale_state
        self.telegram_service.reply_with_back_markup.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_scale_type_back_option(self) -> None:
        self.telegram_message.text = "Back"

        actual = await self.sut.check_scale_type(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_PDF_TASK
        self.file_task_service.ask_pdf_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_scale_type_unknown_text(self) -> None:
        self.telegram_message.text = "clearly_unknown"
        actual = await self.sut.check_scale_type(
            self.telegram_update, self.telegram_context
        )
        assert actual == self.WAIT_SCALE_TYPE

    @pytest.mark.asyncio
    async def test_scale_pdf_by_factor(self) -> None:
        scale_text = "0.1 0.2"
        scale_data = ScaleData.from_string(scale_text)

        self.telegram_message.text = scale_text
        self.pdf_service.scale_pdf.return_value.__enter__.return_value = self.FILE_PATH

        actual = await self.sut.scale_pdf_by_factor(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self.pdf_service.scale_pdf.assert_called_once_with(
            self.TELEGRAM_DOCUMENT_ID, scale_data
        )

    @pytest.mark.asyncio
    async def test_scale_pdf_by_factor_invalid_value(self) -> None:
        self.telegram_message.text = "clearly_invalid"

        actual = await self.sut.scale_pdf_by_factor(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_SCALE_FACTOR
        self.telegram_update.effective_message.reply_text.assert_called_once()
        self.pdf_service.scale_pdf.assert_not_called()

    @pytest.mark.asyncio
    async def test_scale_pdf_by_factor_back_option(self) -> None:
        self.telegram_message.text = "Back"

        actual = await self.sut.scale_pdf_by_factor(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_SCALE_TYPE
        self.telegram_update.effective_message.reply_text.assert_called_once()
        self.pdf_service.scale_pdf.assert_not_called()

    @pytest.mark.asyncio
    async def test_scale_pdf_to_dimension(self) -> None:
        scale_text = "10 20"
        scale_data = ScaleData.from_string(scale_text)

        self.telegram_message.text = scale_text
        self.pdf_service.scale_pdf.return_value.__enter__.return_value = self.FILE_PATH

        actual = await self.sut.scale_pdf_to_dimension(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self.pdf_service.scale_pdf.assert_called_once_with(
            self.TELEGRAM_DOCUMENT_ID, scale_data
        )

    @pytest.mark.asyncio
    async def test_scale_pdf_to_dimension_invalid_value(self) -> None:
        self.telegram_message.text = "clearly_invalid"

        actual = await self.sut.scale_pdf_to_dimension(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_SCALE_DIMENSION
        self.telegram_update.effective_message.reply_text.assert_called_once()
        self.pdf_service.scale_pdf.assert_not_called()

    @pytest.mark.asyncio
    async def test_scale_pdf_to_dimension_back_option(self) -> None:
        self.telegram_message.text = "Back"

        actual = await self.sut.scale_pdf_to_dimension(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_SCALE_TYPE
        self.telegram_update.effective_message.reply_text.assert_called_once()
        self.pdf_service.scale_pdf.assert_not_called()
