from unittest.mock import MagicMock

import pytest
from telegram.constants import FileSizeLimit
from telegram.ext import ConversationHandler

from pdf_bot.file import FileService
from pdf_bot.image_processor import ImageTaskProcessor
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestFileService(LanguageServiceTestMixin, TelegramServiceTestMixin, TelegramTestMixin):
    STATE = "state"

    def setup_method(self) -> None:
        super().setup_method()
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()
        self.image_task_processor = MagicMock(spec=ImageTaskProcessor)
        self.pdf_task_processor = MagicMock(spec=ImageTaskProcessor)

        self.sut = FileService(
            self.telegram_service,
            self.language_service,
            self.image_task_processor,
            self.pdf_task_processor,
        )

    @pytest.mark.asyncio
    async def test_check_pdf(self) -> None:
        self.telegram_document.file_size = FileSizeLimit.FILESIZE_DOWNLOAD
        self.pdf_task_processor.ask_task.return_value = self.STATE

        actual = await self.sut.check_pdf(self.telegram_update, self.telegram_context)

        assert actual == self.STATE
        self.pdf_task_processor.ask_task.assert_called_once_with(
            self.telegram_update, self.telegram_context
        )

    @pytest.mark.asyncio
    async def test_check_pdf_too_big(self) -> None:
        self.telegram_document.file_size = FileSizeLimit.FILESIZE_DOWNLOAD + 1

        actual = await self.sut.check_pdf(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.pdf_task_processor.ask_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_image(self) -> None:
        self.telegram_document.file_size = FileSizeLimit.FILESIZE_DOWNLOAD
        self.image_task_processor.ask_task.return_value = self.STATE

        actual = await self.sut.check_image(self.telegram_update, self.telegram_context)

        assert actual == self.STATE
        self.image_task_processor.ask_task.assert_called_once_with(
            self.telegram_update, self.telegram_context
        )

    @pytest.mark.asyncio
    async def test_check_image_too_big(self) -> None:
        self.telegram_document.file_size = FileSizeLimit.FILESIZE_DOWNLOAD + 1

        actual = await self.sut.check_image(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.pdf_task_processor.ask_task.assert_not_called()
