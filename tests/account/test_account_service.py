from typing import cast
from unittest.mock import MagicMock

import pytest
from telegram import User

from pdf_bot.account.account_repository import AccountRepository
from pdf_bot.account.account_service import AccountService

_LANGUAGE_CODE = "en_GB"


@pytest.fixture(name="account_repository")
def fixture_account_repository() -> AccountRepository:
    return cast(AccountRepository, MagicMock())


@pytest.fixture(name="account_service")
def fixture_account_service(account_repository: AccountRepository) -> AccountService:
    return AccountService(account_repository)


def test_create_user(
    account_service: AccountService,
    account_repository: AccountRepository,
    telegram_user: User,
):
    account_service.create_user(telegram_user)
    account_repository.upsert_user.assert_called_with(telegram_user.id, _LANGUAGE_CODE)


def test_create_user_with_language_code(
    account_service: AccountService,
    account_repository: AccountRepository,
    telegram_user: User,
):
    telegram_user.language_code = "it"
    account_service.create_user(telegram_user)
    account_repository.upsert_user.assert_called_with(telegram_user.id, "it_IT")


def test_create_user_with_invalid_language_code(
    account_service: AccountService,
    account_repository: AccountRepository,
    telegram_user: User,
):
    lang_code = "clearly_invalid_code"
    telegram_user.language_code = lang_code
    account_service.create_user(telegram_user)
    account_repository.upsert_user.assert_called_with(telegram_user.id, _LANGUAGE_CODE)
