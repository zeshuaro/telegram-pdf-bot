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

        assert isinstance(actual[0], CommandHandler)
        assert actual[0].commands == {self.SET_LANGUAGE_COMMAND}
        await actual[0].callback(self.telegram_update, self.telegram_context)

        assert isinstance(actual[1], CallbackQueryHandler)
        assert actual[1].pattern == SetLanguageData
        await actual[1].callback(self.telegram_update, self.telegram_context)

        assert isinstance(actual[2], CallbackQueryHandler)
        assert actual[2].pattern == LanguageData
        await actual[2].callback(self.telegram_update, self.telegram_context)

        assert self.language_service.send_language_options.call_count == 2
        self.language_service.update_user_language.assert_called_once_with(
            self.telegram_update, self.telegram_context
        )
