from unittest.mock import MagicMock

import pytest
from telegram.ext import ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.pdf import PdfService, PdfServiceError
from pdf_bot.telegram_internal import TelegramGetUserDataError, TelegramServiceError
from pdf_bot.watermark import WatermarkService
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestWatermarkService(
    LanguageServiceTestMixin, TelegramServiceTestMixin, TelegramTestMixin
):
    FILE_PATH = "file_path"
    WAIT_SOURCE_PDF = 0
    WAIT_WATERMARK_PDF = 1
    WATERMARK_KEY = "watermark"
    SOURCE_FILE_ID = "source_file_id"

    def setup_method(self) -> None:
        super().setup_method()
        self.pdf_service = MagicMock(spec=PdfService)
        self.language_service = self.mock_language_service()

        self.telegram_service = self.mock_telegram_service()
        self.telegram_service.get_user_data.side_effect = None
        self.telegram_service.get_user_data.return_value = self.SOURCE_FILE_ID

        self.sut = WatermarkService(
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

    @pytest.mark.asyncio
    async def test_ask_source_pdf(self) -> None:
        actual = await self.sut.ask_source_pdf(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_SOURCE_PDF
        self.telegram_service.reply_with_cancel_markup.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_source_pdf(self) -> None:
        actual = await self.sut.check_source_pdf(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_WATERMARK_PDF
        self.telegram_service.check_pdf_document.assert_called_once_with(
            self.telegram_message
        )
        self.telegram_context.user_data.__setitem__.assert_called_once_with(
            self.WATERMARK_KEY, self.TELEGRAM_DOCUMENT_ID
        )
        self.telegram_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_source_pdf_invalid_pdf(self) -> None:
        self.telegram_service.check_pdf_document.side_effect = TelegramServiceError()

        actual = await self.sut.check_source_pdf(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_SOURCE_PDF
        self.telegram_service.check_pdf_document.assert_called_once_with(
            self.telegram_message
        )
        self.telegram_context.user_data.__setitem__.assert_not_called()
        self.telegram_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_watermark_to_pdf(self) -> None:
        self.pdf_service.add_watermark_to_pdf.return_value.__aenter__.return_value = (
            self.FILE_PATH
        )

        actual = await self.sut.add_watermark_to_pdf(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self.telegram_service.check_pdf_document.assert_called_once_with(
            self.telegram_message
        )
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, self.WATERMARK_KEY
        )
        self.pdf_service.add_watermark_to_pdf.assert_called_once_with(
            self.SOURCE_FILE_ID, self.TELEGRAM_DOCUMENT_ID
        )
        self.telegram_service.send_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            self.FILE_PATH,
            TaskType.watermark_pdf,
        )

    @pytest.mark.asyncio
    async def test_add_watermark_to_pdf_service_error(self) -> None:
        self.pdf_service.add_watermark_to_pdf.side_effect = PdfServiceError()

        actual = await self.sut.add_watermark_to_pdf(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self.telegram_service.check_pdf_document.assert_called_once_with(
            self.telegram_message
        )
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, self.WATERMARK_KEY
        )
        self.pdf_service.add_watermark_to_pdf.assert_called_once_with(
            self.SOURCE_FILE_ID, self.TELEGRAM_DOCUMENT_ID
        )
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_watermark_to_pdf_invalid_user_data(self) -> None:
        self.telegram_service.get_user_data.side_effect = TelegramGetUserDataError()

        actual = await self.sut.add_watermark_to_pdf(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self.telegram_service.check_pdf_document.assert_called_once_with(
            self.telegram_message
        )
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, self.WATERMARK_KEY
        )
        self.pdf_service.add_watermark_to_pdf.assert_not_called()
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_watermark_to_pdf_invalid_pdf(self) -> None:
        self.telegram_service.check_pdf_document.side_effect = TelegramServiceError()

        actual = await self.sut.add_watermark_to_pdf(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_WATERMARK_PDF
        self.telegram_service.check_pdf_document.assert_called_once_with(
            self.telegram_message
        )
        self.telegram_service.get_user_data.assert_not_called()
        self.pdf_service.add_watermark_to_pdf.assert_not_called()
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_text_back_option(self) -> None:
        self.telegram_message.text = "Back"
        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)
        assert actual == self.WAIT_SOURCE_PDF

    @pytest.mark.asyncio
    async def test_check_text_cancel_option(self) -> None:
        self.telegram_message.text = "Cancel"

        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.cancel_conversation.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_text_unknown_text(self) -> None:
        self.telegram_message.text = "clearly_unknown"
        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)
        assert actual is None
