from unittest.mock import MagicMock, patch

from requests import Session

from pdf_bot.analytics import AnalyticsRepository


class TestAnalyticsRepository:
    API_SECRET = "api_secret"
    MEASUREMENT_ID = "measurement_id"
    EVENT = {"analytics": "event"}

    def setup_method(self) -> None:
        self.session = MagicMock(spec=Session)

        self.os_patcher = patch("pdf_bot.analytics.analytics_repository.os")
        self.os = self.os_patcher.start()

    def teardown_method(self) -> None:
        self.os_patcher.stop()

    def test_send_event(self) -> None:
        self.os.environ = {
            "GA_API_SECRET": self.API_SECRET,
            "GA_MEASUREMENT_ID": self.MEASUREMENT_ID,
        }
        sut = AnalyticsRepository(self.session)

        sut.send_event(self.EVENT)

        self.session.post.assert_called_once_with(
            "https://www.google-analytics.com/mp/collect",
            params={
                "api_secret": self.API_SECRET,
                "measurement_id": self.MEASUREMENT_ID,
            },
            json=self.EVENT,
            timeout=10,
        )

    def test_send_event_without_secret(self) -> None:
        self.os.environ = {}
        sut = AnalyticsRepository(self.session)

        sut.send_event(self.EVENT)

        self.session.post.assert_not_called()
