from unittest.mock import MagicMock

from requests import Response, Session

from pdf_bot.pdf import FontData
from pdf_bot.text import TextRepository


class TestTextRepository:
    FONT_FAMILY = "font_family"
    FONT_URL = "font_url"

    def setup_method(self) -> None:
        self.response = MagicMock(spec=Response)
        self.response.json.return_value = {
            "items": [{"family": self.FONT_FAMILY, "files": {"regular": self.FONT_URL}}]
        }

        self.session = MagicMock(spec=Session)
        self.session.get.return_value = self.response

        self.sut = TextRepository(self.session)

    def test_get_font(self) -> None:
        actual = self.sut.get_font(self.FONT_FAMILY)

        assert actual == FontData(self.FONT_FAMILY, self.FONT_URL)
        self._assert_api_call()

    def test_get_font_no_regular_font(self) -> None:
        self.response.json.return_value = {
            "items": [{"family": self.FONT_FAMILY, "files": {}}]
        }

        actual = self.sut.get_font(self.FONT_FAMILY)

        assert actual is None
        self._assert_api_call()

    def test_get_font_unknown_font(self) -> None:
        actual = self.sut.get_font("clearly_unknown_font")

        assert actual is None
        self._assert_api_call()

    def _assert_api_call(self) -> None:
        args = self.session.get.call_args[0]
        assert args[0].startswith(
            "https://www.googleapis.com/webfonts/v1/webfonts?key="
        )
