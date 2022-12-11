from loguru import logger
from sentry_sdk import capture_exception
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class FeedbackRepository:
    _SLACK_CHANNEL = "#pdf-bot-feedback"

    def __init__(self, slack_client: WebClient) -> None:
        self.slack_client = slack_client

    def save_feedback(self, chat_id: int, username: str, feedback: str) -> None:
        try:
            text = f"Feedback received from @{username} ({chat_id}):\n\n{feedback}"
            self.slack_client.chat_postMessage(channel=self._SLACK_CHANNEL, text=text)
        except SlackApiError as e:
            logger.exception("Failed to send feedback to Slack")
            capture_exception(e)
