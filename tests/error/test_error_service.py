import pytest

from pdf_bot.error import ErrorService
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramTestMixin


class TestErrorService(LanguageServiceTestMixin, TelegramTestMixin):
    def setup_method(self) -> None:
        super().setup_method()
        self.language_service = self.mock_language_service()

        self.sut = ErrorService(self.language_service)

    @pytest.mark.asyncio
    async def test_process_unknown_callback_query(self) -> None:
        await self.sut.process_unknown_callback_query(self.telegram_update, self.telegram_context)

        self.telegram_callback_query.answer.assert_called_once()
        self.telegram_update.effective_message.reply_text.assert_called_once()
