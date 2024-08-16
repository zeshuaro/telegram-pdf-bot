from unittest.mock import MagicMock

import pytest
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler

from pdf_bot.consts import TEXT_FILTER
from pdf_bot.text import TextHandler, TextService
from tests.telegram_internal import TelegramServiceTestMixin


class TestTextHandler(TelegramServiceTestMixin):
    TEXT_COMMAND = "text"
    CANCEL_COMMAND = "cancel"

    def setup_method(self) -> None:
        super().setup_method()
        self.text_service = MagicMock(spec=TextService)
        self.telegram_service = self.mock_telegram_service()

        self.sut = TextHandler(self.text_service, self.telegram_service)

    @pytest.mark.asyncio
    async def test_conversation_handler(self) -> None:
        actual = self.sut.handlers
        assert len(actual) == 1

        handler = actual[0]
        assert isinstance(handler, ConversationHandler)

        entry_points = handler.entry_points
        assert len(entry_points) == 1
        assert isinstance(entry_points[0], CommandHandler)
        assert entry_points[0].commands == {self.TEXT_COMMAND}

        states = handler.states
        assert TextService.WAIT_TEXT in states
        wait_text = states[TextService.WAIT_TEXT]
        assert len(wait_text) == 1

        assert isinstance(wait_text[0], MessageHandler)
        assert wait_text[0].filters == TEXT_FILTER

        assert TextService.WAIT_FONT in states
        wait_font = states[TextService.WAIT_FONT]
        assert len(wait_font) == 1

        assert isinstance(wait_font[0], MessageHandler)
        assert wait_font[0].filters == TEXT_FILTER

        fallbacks = handler.fallbacks
        assert len(fallbacks) == 1

        assert isinstance(fallbacks[0], CommandHandler)
        assert fallbacks[0].commands == {self.CANCEL_COMMAND}

        for handler in entry_points + wait_text + wait_font + fallbacks:
            await handler.callback(self.telegram_update, self.telegram_context)

        self.text_service.ask_pdf_text.assert_called_once()
        self.text_service.ask_pdf_font.assert_called_once()
        self.text_service.check_text.assert_called_once()
        self.telegram_service.cancel_conversation.assert_called_once()
