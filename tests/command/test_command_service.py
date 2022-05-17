from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from telegram import Update, User
from telegram.ext import CallbackContext

from pdf_bot.account import AccountService
from pdf_bot.command import CommandService


@pytest.fixture(name="account_service")
def fixture_account_service() -> AccountService:
    return cast(AccountService, MagicMock())


@pytest.fixture(name="command_service")
def fixture_command_service(account_service: AccountService) -> CommandService:
    return CommandService(account_service)


def test_send_start_message(
    command_service: CommandService,
    account_service: AccountService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_user: User,
):
    with patch("pdf_bot.command.command_service.set_lang") as _:
        command_service.send_start_message(telegram_update, telegram_context)
        account_service.create_user.assert_called_with(telegram_user)
        telegram_update.effective_message.reply_text.assert_called_once()
