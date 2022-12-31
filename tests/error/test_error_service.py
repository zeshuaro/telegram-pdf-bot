import pytest
from telegram.error import BadRequest

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
        await self.sut.process_unknown_callback_query(
            self.telegram_update, self.telegram_context
        )

        self.telegram_callback_query.answer.assert_called_once()
        self.telegram_callback_query.edit_message_text.assert_called_once()
        self.telegram_callback_query.delete_message.assert_not_called()
        self.telegram_update.effective_message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_unknown_callback_query_edit_bad_request(self) -> None:
        self.telegram_callback_query.edit_message_text.side_effect = BadRequest("Error")
        await self.sut.process_unknown_callback_query(
            self.telegram_update, self.telegram_context
        )
        self._assert_edit_delete_reply_text()

    @pytest.mark.asyncio
    async def test_process_unknown_callback_query_edit_delete_bad_request(self) -> None:
        err = BadRequest("Error")
        self.telegram_callback_query.edit_message_text.side_effect = err
        self.telegram_callback_query.delete_message.side_effect = err

        await self.sut.process_unknown_callback_query(
            self.telegram_update, self.telegram_context
        )

        self._assert_edit_delete_reply_text()

    def _assert_edit_delete_reply_text(self) -> None:
        self.telegram_callback_query.answer.assert_called_once()
        self.telegram_callback_query.edit_message_text.assert_called_once()
        self.telegram_callback_query.delete_message.assert_called_once()
        self.telegram_update.effective_message.reply_text.assert_called_once()
