from unittest.mock import MagicMock

from telegram.ext import ConversationHandler

from pdf_bot.feedback import (
    FeedbackHandler,
    FeedbackInvalidLanguageError,
    FeedbackService,
)
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestFeedbackHandler(
    LanguageServiceTestMixin, TelegramServiceTestMixin, TelegramTestMixin
):
    FEEDBACK_COMMAND = "feedback"
    WAIT_FEEDBACK = 0
    FEEDBACK_TEXT = "feedback_text"
    CANCEL = "Cancel"

    def setup_method(self) -> None:
        super().setup_method()
        self.feedback_service = MagicMock(spec=FeedbackService)
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = FeedbackHandler(
            self.feedback_service,
            self.language_service,
            self.telegram_service,
        )

    def test_conversation_handler(self) -> None:
        actual = self.sut.conversation_handler()
        assert isinstance(actual, ConversationHandler)

    def test_ask_feedback(self) -> None:
        actual = self.sut.ask_feedback(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_FEEDBACK
        self.telegram_service.reply_with_cancel_markup.assert_called_once()

    def test_check_text_save_feedback(self) -> None:
        self.telegram_message.text = self.FEEDBACK_TEXT

        actual = self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self._assert_save_feedback_and_reply_text()

    def test_check_text_save_feedback_error(self) -> None:
        self.telegram_message.text = self.FEEDBACK_TEXT
        self.feedback_service.save_feedback.side_effect = FeedbackInvalidLanguageError()

        actual = self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_FEEDBACK
        self._assert_save_feedback_and_reply_text()

    def test_check_text_cancel(self) -> None:
        self.telegram_message.text = self.CANCEL

        actual = self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.cancel_conversation.assert_called_once_with(
            self.telegram_update, self.telegram_context
        )
        self.feedback_service.save_feedback.assert_not_called()

    def _assert_save_feedback_and_reply_text(self) -> None:
        self.feedback_service.save_feedback.assert_called_once_with(
            self.telegram_chat_id, self.telegram_username, self.FEEDBACK_TEXT
        )
        self.telegram_update.effective_message.reply_text.assert_called_once()
