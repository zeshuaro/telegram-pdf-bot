from unittest.mock import MagicMock

import pytest
from telegram.ext import CallbackQueryHandler

from pdf_bot.error import ErrorCallbackQueryHandler, ErrorService
from tests.telegram_internal import TelegramServiceTestMixin


class TestErrorCallbackQueryHandler(TelegramServiceTestMixin):
    def setup_method(self) -> None:
        super().setup_method()
        self.error_service = MagicMock(spec=ErrorService)

        self.sut = ErrorCallbackQueryHandler(self.error_service)

    @pytest.mark.asyncio
    async def test_handlers(self) -> None:
        actual = self.sut.handlers
        assert len(actual) == 1

        handler = actual[0]
        assert isinstance(handler, CallbackQueryHandler)

        await handler.callback(self.telegram_update, self.telegram_context)
        self.error_service.process_unknown_callback_query.process_unknown_callback_query()
