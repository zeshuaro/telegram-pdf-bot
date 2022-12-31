import re
from unittest.mock import MagicMock

import pytest
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from pdf_bot.file import FileHandler, FileService
from pdf_bot.file_processor import AbstractFileProcessor
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestFileHandler(TelegramServiceTestMixin, TelegramTestMixin):
    STATE = "state"

    def setup_method(self) -> None:
        super().setup_method()
        self.file_service = MagicMock(spec=FileService)
        self.telegram_service = self.mock_telegram_service()

        self.sut = FileHandler(self.file_service, self.telegram_service)

    @pytest.mark.asyncio
    async def test_handlers(self) -> None:
        actual = self.sut.handlers
        assert len(actual) == 1

        handler = actual[0]
        assert isinstance(handler, ConversationHandler)

        entry_points = handler.entry_points
        assert len(entry_points) == 2

        assert isinstance(entry_points[0], MessageHandler)
        assert entry_points[0].filters == filters.Document.PDF

        assert isinstance(entry_points[1], MessageHandler)
        assert entry_points[1].filters.name == (filters.PHOTO | filters.Document.IMAGE).name

        assert AbstractFileProcessor.WAIT_FILE_TASK in handler.states

        fallbacks = handler.fallbacks
        assert len(fallbacks) == 2

        assert isinstance(fallbacks[0], CallbackQueryHandler)
        assert fallbacks[0].pattern == re.compile(r"^cancel$")

        assert isinstance(fallbacks[1], CommandHandler)
        assert fallbacks[1].commands == {"cancel"}

        assert handler.allow_reentry is True

        for handler in entry_points + fallbacks:
            await handler.callback(self.telegram_update, self.telegram_context)

        self.file_service.check_pdf.assert_called_once()
        self.file_service.check_image.assert_called_once()
        assert self.telegram_service.cancel_conversation.call_count == 2
