import pytest
from telegram.ext import CallbackQueryHandler, CommandHandler

from pdf_bot.language import LanguageData, LanguageHandler, SetLanguageData
from tests.telegram_internal import TelegramTestMixin

from .language_service_test_mixin import LanguageServiceTestMixin


class TestLanguageHandler(LanguageServiceTestMixin, TelegramTestMixin):
    SET_LANGUAGE_COMMAND = "setlang"

    def setup_method(self) -> None:
        super().setup_method()
        self.language_service = self.mock_language_service()
        self.sut = LanguageHandler(self.language_service)

    @pytest.mark.asyncio
    async def test_handlers(self) -> None:
        actual = self.sut.handlers
        assert len(actual) == 3
        handler_0, handler_1, handler_2 = actual

        assert isinstance(handler_0, CommandHandler)
        assert handler_0.commands == {self.SET_LANGUAGE_COMMAND}

        assert isinstance(handler_1, CallbackQueryHandler)
        assert handler_1.pattern == SetLanguageData

        assert isinstance(handler_2, CallbackQueryHandler)
        assert handler_2.pattern == LanguageData

        for handler in actual:
            await handler.callback(self.telegram_update, self.telegram_context)

        assert self.language_service.send_language_options.call_count == 2
        self.language_service.update_user_language.assert_called_once_with(
            self.telegram_update, self.telegram_context
        )
