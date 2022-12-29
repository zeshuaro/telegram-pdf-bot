import re
from unittest.mock import MagicMock

import pytest
from telegram.constants import FileSizeLimit
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from pdf_bot.file_handler import FileHandler
from pdf_bot.file_processor import AbstractFileProcessor
from pdf_bot.image_processor import ImageTaskProcessor
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestFileHandler(
    LanguageServiceTestMixin, TelegramServiceTestMixin, TelegramTestMixin
):
    STATE = "state"

    def setup_method(self) -> None:
        super().setup_method()
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()
        self.image_task_processor = MagicMock(spec=ImageTaskProcessor)
        self.pdf_task_processor = MagicMock(spec=ImageTaskProcessor)

        self.sut = FileHandler(
            self.telegram_service,
            self.language_service,
            self.image_task_processor,
            self.pdf_task_processor,
        )

    @pytest.mark.asyncio
    async def test_conversation_handler(self) -> None:
        actual = self.sut.conversation_handler()
        assert isinstance(actual, ConversationHandler)

        entry_points = actual.entry_points
        assert len(entry_points) == 2

        assert isinstance(entry_points[0], MessageHandler)
        assert entry_points[0].filters == filters.Document.PDF

        assert isinstance(entry_points[1], MessageHandler)
        assert (
            entry_points[1].filters.name
            == (filters.PHOTO | filters.Document.IMAGE).name
        )

        assert AbstractFileProcessor.WAIT_FILE_TASK in actual.states

        fallbacks = actual.fallbacks
        assert len(fallbacks) == 2

        assert isinstance(fallbacks[0], CallbackQueryHandler)
        assert fallbacks[0].pattern == re.compile(r"^cancel$")

        assert isinstance(fallbacks[1], CommandHandler)
        assert fallbacks[1].commands == {"cancel"}

        assert actual.allow_reentry is True

    @pytest.mark.asyncio
    async def test_check_pdf(self) -> None:
        self.telegram_document.file_size = FileSizeLimit.FILESIZE_DOWNLOAD
        self.pdf_task_processor.ask_task.return_value = self.STATE

        actual = await self.sut._check_pdf(self.telegram_update, self.telegram_context)

        assert actual == self.STATE
        self.pdf_task_processor.ask_task.assert_called_once_with(
            self.telegram_update, self.telegram_context
        )

    @pytest.mark.asyncio
    async def test_check_pdf_too_big(self) -> None:
        self.telegram_document.file_size = FileSizeLimit.FILESIZE_DOWNLOAD + 1

        actual = await self.sut._check_pdf(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.pdf_task_processor.ask_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_image(self) -> None:
        self.telegram_document.file_size = FileSizeLimit.FILESIZE_DOWNLOAD
        self.image_task_processor.ask_task.return_value = self.STATE

        actual = await self.sut._check_image(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.STATE
        self.image_task_processor.ask_task.assert_called_once_with(
            self.telegram_update, self.telegram_context
        )

    @pytest.mark.asyncio
    async def test_check_image_too_big(self) -> None:
        self.telegram_document.file_size = FileSizeLimit.FILESIZE_DOWNLOAD + 1

        actual = await self.sut._check_image(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self.pdf_task_processor.ask_task.assert_not_called()
