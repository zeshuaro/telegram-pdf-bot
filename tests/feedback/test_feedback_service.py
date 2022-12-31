from unittest.mock import MagicMock, patch

import pytest
from telegram.ext import ConversationHandler

from pdf_bot.feedback import FeedbackRepository, FeedbackService
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestFeedbackService(LanguageServiceTestMixin, TelegramServiceTestMixin, TelegramTestMixin):
    WAIT_FEEDBACK = 0
    VALID_LANGUAGE_CODE = "en"
    CANCEL = "Cancel"

    def setup_method(self) -> None:
        super().setup_method()
        self.feedback_repository = MagicMock(spec=FeedbackRepository)
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = FeedbackService(
            self.feedback_repository, self.language_service, self.telegram_service
        )

        self.detect_patcher = patch(
            "pdf_bot.feedback.feedback_service.detect",
            return_value=self.VALID_LANGUAGE_CODE,
        )
        self.detect = self.detect_patcher.start()

    def teardown_method(self) -> None:
        self.detect_patcher.stop()
        super().teardown_method()

    @pytest.mark.asyncio
    async def test_ask_feedback(self) -> None:
        actual = await self.sut.ask_feedback(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_FEEDBACK
        self.telegram_service.reply_with_cancel_markup.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_text_save_feedback(self) -> None:
        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self._assert_save_feedback_and_reply_text()

    @pytest.mark.asyncio
    async def test_check_text_save_feedback_invalid_language(self) -> None:
        self.detect.return_value = "clearly_invalid_language"

        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_FEEDBACK
        self.feedback_repository.save_feedback.assert_not_called()
        self.telegram_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_text_cancel(self) -> None:
        self.telegram_message.text = self.CANCEL

        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.cancel_conversation.assert_called_once_with(
            self.telegram_update, self.telegram_context
        )
        self.feedback_repository.save_feedback.assert_not_called()

    def _assert_save_feedback_and_reply_text(self) -> None:
        self.feedback_repository.save_feedback.assert_called_once_with(
            self.TELEGRAM_CHAT_ID, self.TELEGRAM_USERNAME, self.TELEGRAM_TEXT
        )
        self.telegram_update.effective_message.reply_text.assert_called_once()
