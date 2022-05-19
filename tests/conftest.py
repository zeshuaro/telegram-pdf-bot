import random
import string
from typing import cast
from unittest.mock import MagicMock

import pytest
from telegram import Bot, Document, File, Message, Update, User
from telegram.ext import CallbackContext


@pytest.fixture(name="user_id")
def fixture_user_id() -> int:
    return random.randint(0, 100)


@pytest.fixture(name="document_id")
def fixture_document_id() -> str:
    return "".join(random.choices(string.ascii_letters, k=10))


@pytest.fixture
def language_code() -> str:
    return "en_GB"


@pytest.fixture(name="telegram_user")
def fixture_telegram_user(user_id: int) -> User:
    user = cast(User, MagicMock())
    user.id = user_id
    return user


@pytest.fixture(name="telegram_document")
def fixture_telegram_document(document_id: int) -> Document:
    doc = cast(Document, MagicMock())
    doc.file_id = document_id
    return doc


@pytest.fixture(name="telegram_file")
def fixture_telegram_file() -> Document:
    return cast(File, MagicMock())


@pytest.fixture(name="telegram_message")
def fixture_telegram_message(
    telegram_user: User, telegram_document: Document
) -> Message:
    msg = cast(Message, MagicMock())
    msg.from_user = telegram_user
    msg.document = telegram_document
    return msg


@pytest.fixture()
def telegram_bot() -> Bot:
    return cast(Bot, MagicMock())


@pytest.fixture
def telegram_update(telegram_message: Message) -> Update:
    update = cast(Update, MagicMock())
    update.effective_message = telegram_message
    return update


@pytest.fixture
def telegram_context() -> CallbackContext:
    context = cast(CallbackContext, MagicMock())
    return context
