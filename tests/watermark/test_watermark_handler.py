from unittest.mock import MagicMock

import pytest
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters

from pdf_bot.consts import TEXT_FILTER
from pdf_bot.watermark import WatermarkHandler, WatermarkService
from tests.telegram_internal import TelegramServiceTestMixin


class TestWatermarkHandler(TelegramServiceTestMixin):
    WATERMARK_COMMAND = "watermark"
    CANCEL_COMMAND = "cancel"

    def setup_method(self) -> None:
        super().setup_method()
        self.watermark_service = MagicMock(spec=WatermarkService)
        self.telegram_service = self.mock_telegram_service()

        self.sut = WatermarkHandler(self.watermark_service, self.telegram_service)

    @pytest.mark.asyncio
    async def test_conversation_handler(self) -> None:
        actual = self.sut.handlers
        assert len(actual) == 1

        handler = actual[0]
        assert isinstance(handler, ConversationHandler)

        entry_points = handler.entry_points
        assert len(entry_points) == 1
        assert isinstance(entry_points[0], CommandHandler)
        assert entry_points[0].commands == {self.WATERMARK_COMMAND}

        states = handler.states
        assert WatermarkService.WAIT_SOURCE_PDF in states
        wait_source_pdf = states[WatermarkService.WAIT_SOURCE_PDF]
        assert len(wait_source_pdf) == 1

        assert isinstance(wait_source_pdf[0], MessageHandler)
        assert wait_source_pdf[0].filters == filters.Document.PDF

        assert WatermarkService.WAIT_WATERMARK_PDF in states
        wait_watermark_pdf = states[WatermarkService.WAIT_WATERMARK_PDF]
        assert len(wait_watermark_pdf) == 1

        assert isinstance(wait_watermark_pdf[0], MessageHandler)
        assert wait_watermark_pdf[0].filters == filters.Document.PDF

        fallbacks = handler.fallbacks
        assert len(fallbacks) == 2

        assert isinstance(fallbacks[0], CommandHandler)
        assert fallbacks[0].commands == {self.CANCEL_COMMAND}

        assert isinstance(fallbacks[1], MessageHandler)
        assert fallbacks[1].filters.name == TEXT_FILTER.name

        for handler in entry_points + wait_source_pdf + wait_watermark_pdf + fallbacks:
            await handler.callback(self.telegram_update, self.telegram_context)

        self.watermark_service.ask_source_pdf.assert_called_once()
        self.watermark_service.check_source_pdf.assert_called_once()
        self.watermark_service.add_watermark_to_pdf.assert_called_once()
        self.watermark_service.check_text.assert_called_once()
        self.telegram_service.cancel_conversation.assert_called_once()
