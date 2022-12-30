from unittest.mock import MagicMock

import pytest
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler

from pdf_bot.consts import TEXT_FILTER
from pdf_bot.feedback import FeedbackHandler, FeedbackService
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestFeedbackHandler(TelegramServiceTestMixin, TelegramTestMixin):
    FEEDBACK_COMMAND = "feedback"
    CANCEL_COMMAND = "cancel"

    def setup_method(self) -> None:
        super().setup_method()
        self.feedback_service = MagicMock(spec=FeedbackService)
        self.telegram_service = self.mock_telegram_service()

        self.sut = FeedbackHandler(
            self.feedback_service,
            self.telegram_service,
        )

    @pytest.mark.asyncio
    async def test_handlers(self) -> None:
        actual = self.sut.handlers
        assert len(actual) == 1

        handler = actual[0]
        assert isinstance(handler, ConversationHandler)

        entry_points = handler.entry_points
        assert len(entry_points) == 1
        assert isinstance(entry_points[0], CommandHandler)
        assert entry_points[0].commands == {self.FEEDBACK_COMMAND}

        states = handler.states
        assert FeedbackService.WAIT_FEEDBACK in states
        wait_feedback = states[FeedbackService.WAIT_FEEDBACK]
        assert len(wait_feedback) == 1
        assert isinstance(wait_feedback[0], MessageHandler)
        assert wait_feedback[0].filters.name == TEXT_FILTER.name

        fallbacks = handler.fallbacks
        assert len(fallbacks) == 1

        assert isinstance(fallbacks[0], CommandHandler)
        assert fallbacks[0].commands == {self.CANCEL_COMMAND}

        for handler in entry_points + wait_feedback + fallbacks:
            await handler.callback(self.telegram_update, self.telegram_context)

        self.feedback_service.ask_feedback.assert_called_once()
        self.feedback_service.check_text.assert_called_once()
        self.telegram_service.cancel_conversation.assert_called_once()
