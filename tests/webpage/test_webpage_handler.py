from unittest.mock import MagicMock

import pytest
from telegram import MessageEntity
from telegram.ext import MessageHandler, filters

from pdf_bot.webpage import WebpageHandler, WebpageService
from tests.telegram_internal import TelegramTestMixin


class TestWebpageHandler(TelegramTestMixin):
    def setup_method(self) -> None:
        super().setup_method()
        self.webpage_service = MagicMock(spec=WebpageService)
        self.sut = WebpageHandler(self.webpage_service)

    @pytest.mark.asyncio
    async def test_handlers(self) -> None:
        actual = self.sut.handlers
        assert len(actual) == 1

        handler = actual[0]
        assert isinstance(handler, MessageHandler)
        assert handler.filters.name == filters.Entity(MessageEntity.URL).name

        for handler in actual:
            await handler.callback(self.telegram_update, self.telegram_context)

        self.webpage_service.url_to_pdf.assert_called_once()
