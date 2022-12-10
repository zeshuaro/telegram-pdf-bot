import os
from typing import Any

from dotenv import load_dotenv
from loguru import logger
from requests import Session

load_dotenv()


class AnalyticsRepository:
    def __init__(self, api_client: Session) -> None:
        self.api_client = api_client

        self.api_secret = os.environ.get("GA_API_SECRET")
        self.measurement_id = os.environ.get("GA_MEASUREMENT_ID")

    def send_event(self, event: dict[str, Any]) -> None:
        if self.api_secret is None or self.measurement_id is None:
            logger.error(
                "Missing Google Analytics keys: GA_API_SECRET and GA_MEASUREMENT_ID"
            )
            return

        params = {"api_secret": self.api_secret, "measurement_id": self.measurement_id}
        self.api_client.post(
            "https://www.google-analytics.com/mp/collect",
            params=params,
            json=event,
            timeout=10,
        )
