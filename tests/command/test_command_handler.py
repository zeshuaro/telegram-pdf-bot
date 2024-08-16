from unittest.mock import MagicMock

import pytest
from telegram.ext import CommandHandler, filters

from pdf_bot.command import CommandService, MyCommandHandler
from tests.telegram_internal import TelegramTestMixin


class TestCommandHandler(TelegramTestMixin):
    START_COMMAND = "start"
    HELP_COMMAND = "help"
    SEND_COMMAND = "send"
    ADMIN_TELEGRAM_ID = 123

    def setup_method(self) -> None:
        super().setup_method()
        self.command_service = MagicMock(spec=CommandService)
        self.sut = MyCommandHandler(self.command_service, self.ADMIN_TELEGRAM_ID)

    @pytest.mark.asyncio
    async def test_handlers(self) -> None:
        actual = self.sut.handlers
        assert len(actual) == 3
        handler_0, handler_1, handler_2 = actual

        assert isinstance(handler_0, CommandHandler)
        assert handler_0.commands == {self.START_COMMAND}

        assert isinstance(handler_1, CommandHandler)
        assert handler_1.commands == {self.HELP_COMMAND}

        assert isinstance(handler_2, CommandHandler)
        assert handler_2.commands == {self.SEND_COMMAND}
        assert handler_2.filters.name == filters.User(self.ADMIN_TELEGRAM_ID).name

        for handler in actual:
            await handler.callback(self.telegram_update, self.telegram_context)

        self.command_service.send_start_message.assert_called_once()
        self.command_service.send_help_message.assert_called_once()
        self.command_service.send_message_to_user.assert_called_once()
