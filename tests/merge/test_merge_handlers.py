from unittest.mock import MagicMock

from telegram.ext import ConversationHandler

from pdf_bot.merge import MergeHandlers, MergeService
from tests.telegram_internal import TelegramServiceTestMixin


class TestMergeHandlers(TelegramServiceTestMixin):
    def setup_method(self) -> None:
        super().setup_method()
        self.merge_service = MagicMock(spec=MergeService)
        self.telegram_service = self.mock_telegram_service()

        self.sut = MergeHandlers(self.merge_service, self.telegram_service)

    def test_conversation_handler(self) -> None:
        actual = self.sut.conversation_handler()
        assert isinstance(actual, ConversationHandler)
