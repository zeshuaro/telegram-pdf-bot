from unittest.mock import MagicMock

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

    def test_send_start_message(self) -> None:
        self.sut.send_start_message(self.telegram_update, self.telegram_context)

        self.account_service.create_user.assert_called_once_with(self.telegram_user)
        self.telegram_update.effective_message.reply_text.assert_called_once()
