from unittest.mock import ANY, MagicMock

import pytest
from telegram.constants import ParseMode
from telegram.error import Forbidden

from pdf_bot.account import AccountService
from pdf_bot.command import CommandService
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramTestMixin


class TestCommandService(LanguageServiceTestMixin, TelegramTestMixin):
    def setup_method(self) -> None:
        super().setup_method()
        self.account_service = MagicMock(spec=AccountService)
        self.language_service = self.mock_language_service()

        self.sut = CommandService(self.account_service, self.language_service)

    @pytest.mark.asyncio
    async def test_send_start_message(self) -> None:
        await self.sut.send_start_message(self.telegram_update, self.telegram_context)

        self.account_service.create_user.assert_called_once_with(self.telegram_user)
        self.telegram_update.message.reply_text.assert_called_once_with(
            ANY, parse_mode=ParseMode.HTML
        )

    @pytest.mark.asyncio
    async def test_send_help_message(self) -> None:
        await self.sut.send_help_message(self.telegram_update, self.telegram_context)
        self.telegram_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_to_user(self) -> None:
        self.telegram_context.args = [self.TELEGRAM_USER_ID, self.TELEGRAM_TEXT]
        await self.sut.send_message_to_user(self.telegram_update, self.telegram_context)
        self._assert_send_message_to_user("Message sent")

    @pytest.mark.asyncio
    async def test_send_message_to_user_unauthorized(self) -> None:
        self.telegram_context.args = [self.TELEGRAM_USER_ID, self.TELEGRAM_TEXT]
        self.telegram_bot.send_message.side_effect = Forbidden("Error")

        await self.sut.send_message_to_user(self.telegram_update, self.telegram_context)

        self._assert_send_message_to_user("User has blocked the bot")

    def _assert_send_message_to_user(self, message: str) -> None:
        self.telegram_context.bot.send_message.assert_called_once_with(
            self.TELEGRAM_USER_ID, self.TELEGRAM_TEXT
        )
        self.telegram_update.message.reply_text.assert_called_once_with(message)
