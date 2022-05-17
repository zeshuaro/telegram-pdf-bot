import random
from typing import cast
from unittest.mock import MagicMock

import pytest
from telegram import Message, Update, User
from telegram.ext import CallbackContext


@pytest.fixture(name="user_id")
def fixture_user_id() -> int:
    return random.randint(0, 100)


@pytest.fixture
def language_code() -> str:
    return "en_GB"


@pytest.fixture(name="telegram_user")
def fixture_telegram_user(user_id: int) -> User:
    user = cast(User, MagicMock())
    user.id = user_id
    return user


@pytest.fixture(name="telegram_message")
def fixture_telegram_message(telegram_user: User) -> Message:
    msg = cast(Message, MagicMock())
    msg.from_user = telegram_user
    return msg


@pytest.fixture
def telegram_update(telegram_message: Message) -> Update:
    update = cast(Update, MagicMock())
    update.effective_message = telegram_message
    return update


@pytest.fixture
def telegram_context() -> CallbackContext:
    return cast(CallbackContext, MagicMock())
