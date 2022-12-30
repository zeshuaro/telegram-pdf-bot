from unittest.mock import MagicMock

from requests import Session

from pdf_bot.analytics import AnalyticsRepository
from pdf_bot.settings import Settings


class TestAnalyticsRepository:
    EVENT = {"analytics": "event"}

    def setup_method(self) -> None:
        self.session = MagicMock(spec=Session)
        self.settings = Settings()

        self.sut = AnalyticsRepository(self.session, self.settings)

    def test_send_event(self) -> None:
        self.sut.send_event(self.EVENT)
        self.session.post.assert_called_once_with(
            "https://www.google-analytics.com/mp/collect",
            params={
                "api_secret": self.settings.ga_api_secret,
                "measurement_id": self.settings.ga_measurement_id,
            },
            json=self.EVENT,
            timeout=10,
        )
