from unittest.mock import MagicMock

from telegram.ext import ConversationHandler

from pdf_bot.text import TextHandlers, TextService
from tests.telegram_internal import TelegramServiceTestMixin


class TestTextHandlers(TelegramServiceTestMixin):
    def setup_method(self) -> None:
        super().setup_method()
        self.text_service = MagicMock(spec=TextService)
        self.telegram_service = self.mock_telegram_service()

        self.sut = TextHandlers(self.text_service, self.telegram_service)

    def test_conversation_handler(self) -> None:
        actual = self.sut.conversation_handler()
        assert isinstance(actual, ConversationHandler)
