import random
from typing import cast
from unittest.mock import MagicMock

import pytest
from telegram import User


@pytest.fixture(name="user_id")
def fixture_user_id() -> int:
    return random.randint(0, 100)


@pytest.fixture
def language_code() -> str:
    return "en_GB"


@pytest.fixture
def telegram_user(user_id: int) -> User:
    user = cast(User, MagicMock())
    user.id = user_id
    return user
