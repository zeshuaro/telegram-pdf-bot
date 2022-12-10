from unittest.mock import MagicMock

from telegram.ext import ConversationHandler

from pdf_bot.watermark import WatermarkHandlers, WatermarkService
from tests.telegram_internal import TelegramServiceTestMixin


class TestWatermarkHandlers(TelegramServiceTestMixin):
    def setup_method(self) -> None:
        super().setup_method()
        self.watermark_service = MagicMock(spec=WatermarkService)
        self.telegram_service = self.mock_telegram_service()

        self.sut = WatermarkHandlers(self.watermark_service, self.telegram_service)

    def test_conversation_handler(self) -> None:
        actual = self.sut.conversation_handler()
        assert isinstance(actual, ConversationHandler)
