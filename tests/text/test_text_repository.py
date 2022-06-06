from typing import cast
from unittest.mock import MagicMock

import pytest
from requests import Response, Session

from pdf_bot.pdf import FontData
from pdf_bot.text import TextRepository


@pytest.fixture(name="font_family")
def fixture_font_family() -> str:
    return "font_family"


@pytest.fixture(name="font_url")
def fixture_font_url() -> str:
    return "font_url"


@pytest.fixture(name="session")
def fixture_session() -> Session:
    return cast(Session, MagicMock())


@pytest.fixture(name="response")
def fixture_response(font_family: str, font_url: str) -> Response:
    r = cast(Response, MagicMock())
    r.json.return_value = {
        "items": [{"family": font_family, "files": {"regular": font_url}}]
    }
    return r


@pytest.fixture(name="text_repository")
def fixture_text_repository(session: Session) -> TextRepository:
    return TextRepository(session)


def test_get_font(
    text_repository: TextRepository,
    session: Session,
    response: Response,
    font_family: str,
    font_url: str,
) -> None:
    session.get.return_value = response
    actual = text_repository.get_font(font_family)
    assert actual == FontData(font_family, font_url)


def test_get_font_not_found(
    text_repository: TextRepository, session: Session, response: Response
) -> None:
    session.get.return_value = response
    actual = text_repository.get_font("clearly_unknown_font")
    assert actual is None
