from unittest.mock import MagicMock, patch
from uuid import UUID

from requests import HTTPError

from pdf_bot.analytics import (
    AnalyticsRepository,
    AnalyticsService,
    EventAction,
    TaskType,
)
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramTestMixin


class TestAnalyticsService(LanguageServiceTestMixin, TelegramTestMixin):
    TASK_TYPE = TaskType.beautify_image
    EVENT_ACTION = EventAction.complete
    LANGUAGE = "language"

    def setup_method(self) -> None:
        super().setup_method()
        self.analytics_repository = MagicMock(spec=AnalyticsRepository)
        self.language_service = self.mock_language_service()
        self.language_service.get_user_language.return_value = self.LANGUAGE

        self.sut = AnalyticsService(
            self.analytics_repository,
            self.language_service,
        )

    def test_send_event(self) -> None:
        self._test_and_assert_send_event()

    def test_send_event_error(self) -> None:
        self.analytics_repository.send_event.side_effect = HTTPError()

        with patch("pdf_bot.analytics.analytics_service.logger") as logger:
            self._test_and_assert_send_event()
            logger.exception.assert_called_once()

    def _test_and_assert_send_event(self) -> None:
        self.sut.send_event(
            self.telegram_update,
            self.telegram_context,
            self.TASK_TYPE,
            self.EVENT_ACTION,
        )

        self.language_service.get_user_language.assert_called_once_with(
            self.telegram_update, self.telegram_context
        )

        event = {
            "client_id": str(UUID(int=self.TELEGRAM_USER_ID)),
            "user_properties": {"bot_language": {"value": self.LANGUAGE}},
            "events": [
                {
                    "name": self.TASK_TYPE.value,
                    "params": {"action": self.EVENT_ACTION.value},
                }
            ],
        }
        self.analytics_repository.send_event.assert_called_once_with(event)
