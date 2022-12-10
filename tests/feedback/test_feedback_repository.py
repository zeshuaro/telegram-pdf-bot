from unittest.mock import MagicMock, patch

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from pdf_bot.feedback import FeedbackRepository
from tests.telegram_internal import TelegramTestMixin


class TestFeedbackRepository(TelegramTestMixin):
    SLACK_CHANNEL = "#pdf-bot-feedback"

    def setup_method(self) -> None:
        self.slack_client = MagicMock(spec=WebClient)
        self.sut = FeedbackRepository(self.slack_client)

    def test_save_feedback(self) -> None:
        self._save_feedback_and_assert_slack_client()

    def test_save_feedback_error(self) -> None:
        error = SlackApiError("Error", "Response")
        self.slack_client.chat_postMessage.side_effect = error

        with patch("pdf_bot.feedback.feedback_repository.logger") as logger, patch(
            "pdf_bot.feedback.feedback_repository.capture_exception"
        ) as capture_exception:
            self._save_feedback_and_assert_slack_client()

            logger.exception.assert_called_once_with("Failed to send feedback to Slack")
            capture_exception.assert_called_once_with(error)

    def _save_feedback_and_assert_slack_client(self) -> None:
        self.sut.save_feedback(
            self.telegram_chat_id, self.telegram_username, self.telegram_text
        )
        self.slack_client.chat_postMessage.assert_called_once_with(
            channel=self.SLACK_CHANNEL,
            text=(
                "Feedback received from"
                f" @{self.telegram_username} ({self.telegram_chat_id}):\n\n{self.telegram_text}"
            ),
        )
