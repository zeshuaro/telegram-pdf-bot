from unittest.mock import MagicMock

import pytest
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters

from pdf_bot.consts import TEXT_FILTER
from pdf_bot.merge import MergeHandler, MergeService
from tests.telegram_internal import TelegramServiceTestMixin


class TestMergeHandler(TelegramServiceTestMixin):
    MERGE_COMMAND = "merge"
    CANCEL_COMMAND = "cancel"

    def setup_method(self) -> None:
        super().setup_method()
        self.merge_service = MagicMock(spec=MergeService)
        self.telegram_service = self.mock_telegram_service()

        self.sut = MergeHandler(self.merge_service, self.telegram_service)

    @pytest.mark.asyncio
    async def test_conversation_handler(self) -> None:
        actual = self.sut.handlers
        assert len(actual) == 1

        handler = actual[0]
        assert isinstance(handler, ConversationHandler)

        entry_points = handler.entry_points
        assert len(entry_points) == 1
        assert isinstance(entry_points[0], CommandHandler)
        assert entry_points[0].commands == {self.MERGE_COMMAND}

        states = handler.states
        assert MergeService.WAIT_MERGE_PDF in states
        wait_image = states[MergeService.WAIT_MERGE_PDF]
        assert len(wait_image) == 2

        assert isinstance(wait_image[0], MessageHandler)
        assert wait_image[0].filters == filters.Document.PDF

        assert isinstance(wait_image[1], MessageHandler)
        assert wait_image[1].filters.name == TEXT_FILTER.name

        fallbacks = handler.fallbacks
        assert len(fallbacks) == 1

        assert isinstance(fallbacks[0], CommandHandler)
        assert fallbacks[0].commands == {self.CANCEL_COMMAND}

        for handler in entry_points + wait_image + fallbacks:
            await handler.callback(self.telegram_update, self.telegram_context)

        self.merge_service.ask_first_pdf.assert_called_once()
        self.merge_service.check_pdf.assert_called_once()
        self.merge_service.check_text.assert_called_once()
        self.telegram_service.cancel_conversation.assert_called_once()
