from unittest.mock import MagicMock, patch

import pytest

from pdf_bot.feedback import (
    FeedbackInvalidLanguageError,
    FeedbackRepository,
    FeedbackService,
)
from tests.telegram_internal import TelegramTestMixin


class TestFeedbackService(TelegramTestMixin):
    VALID_LANGUAGE_CODE = "en"

    def setup_method(self) -> None:
        super().setup_method()
        self.feedback_repository = MagicMock(spec=FeedbackRepository)
        self.sut = FeedbackService(self.feedback_repository)

        self.detect_patcher = patch(
            "pdf_bot.feedback.feedback_service.detect",
            return_value=self.VALID_LANGUAGE_CODE,
        )
        self.detect = self.detect_patcher.start()

    def teardown_method(self) -> None:
        self.detect_patcher.stop()
        super().teardown_method()

    def test_save_feedback(self) -> None:
        self._save_feedback()
        self.feedback_repository.save_feedback.assert_called_once_with(
            self.telegram_chat_id, self.telegram_username, self.telegram_text
        )

    def test_save_feedback_invalid_language(self) -> None:
        self.detect.return_value = "clearly_invalid_language"
        with pytest.raises(FeedbackInvalidLanguageError):
            self._save_feedback()
        self.feedback_repository.save_feedback.assert_not_called()

    def _save_feedback(self) -> None:
        self.sut.save_feedback(
            self.telegram_chat_id, self.telegram_username, self.telegram_text
        )
