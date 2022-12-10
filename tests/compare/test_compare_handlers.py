from unittest.mock import MagicMock

from telegram.ext import ConversationHandler

from pdf_bot.compare import CompareHandlers, CompareService
from tests.telegram_internal import TelegramServiceTestMixin


class TestCompareHandlers(TelegramServiceTestMixin):
    def setup_method(self) -> None:
        super().setup_method()
        self.compare_service = MagicMock(spec=CompareService)
        self.telegram_service = self.mock_telegram_service()

        self.sut = CompareHandlers(self.compare_service, self.telegram_service)

    def test_conversation_handler(self) -> None:
        actual = self.sut.conversation_handler()
        assert isinstance(actual, ConversationHandler)
