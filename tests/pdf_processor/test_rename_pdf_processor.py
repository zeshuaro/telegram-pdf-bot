from unittest.mock import MagicMock

import pytest
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
)

from pdf_bot.analytics import TaskType
from pdf_bot.file_processor import AbstractFileTaskProcessor
from pdf_bot.models import BackData, TaskData
from pdf_bot.pdf import PdfService
from pdf_bot.pdf_processor import RenamePdfData, RenamePdfProcessor
from tests.file_task import FileTaskServiceTestMixin
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestRenamePdfProcessor(
    FileTaskServiceTestMixin,
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    FILE_PATH = "file_path"
    WAIT_FILE_NAME = "wait_file_name"
    INVALID_CHARACTERS = r"\/*?:\'<>|"

    def setup_method(self) -> None:
        super().setup_method()
        self.telegram_update.callback_query = None

        self.pdf_service = MagicMock(spec=PdfService)
        self.file_task_service = self.mock_file_task_service()
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = RenamePdfProcessor(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
            bypass_init_check=True,
        )

    def test_get_task_type(self) -> None:
        actual = self.sut.task_type
        assert actual == TaskType.rename_pdf

    def test_should_process_back_option(self) -> None:
        actual = self.sut.should_process_back_option
        assert actual is False

    def test_task_data(self) -> None:
        actual = self.sut.task_data
        assert actual == TaskData("Rename", RenamePdfData)

    def test_handler(self) -> None:
        actual = self.sut.handler

        assert isinstance(actual, ConversationHandler)

        entry_points = actual.entry_points
        assert len(entry_points) == 1
        assert isinstance(entry_points[0], CallbackQueryHandler)
        assert entry_points[0].pattern == RenamePdfData

        assert self.WAIT_FILE_NAME in actual.states
        wait_file_name_state = actual.states[self.WAIT_FILE_NAME]
        assert len(wait_file_name_state) == 2

        assert isinstance(wait_file_name_state[0], MessageHandler)
        assert isinstance(wait_file_name_state[1], CallbackQueryHandler)
        assert wait_file_name_state[1].pattern == BackData

        fallbacks = actual.fallbacks
        assert len(fallbacks) == 1
        assert isinstance(fallbacks[0], CommandHandler)
        assert fallbacks[0].commands == {"cancel"}

        map_to_parent = actual.map_to_parent
        assert map_to_parent is not None
        assert AbstractFileTaskProcessor.WAIT_FILE_TASK in map_to_parent
        assert (
            map_to_parent[AbstractFileTaskProcessor.WAIT_FILE_TASK]
            == AbstractFileTaskProcessor.WAIT_FILE_TASK
        )

    @pytest.mark.asyncio
    async def test_process_file_task(self) -> None:
        self.pdf_service.rename_pdf.return_value.__aenter__.return_value = (
            self.FILE_PATH
        )

        async with self.sut.process_file_task(
            self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_TEXT
        ) as actual:
            assert actual == self.FILE_PATH
            self.pdf_service.rename_pdf.assert_called_once_with(
                self.TELEGRAM_DOCUMENT_ID, f"{self.TELEGRAM_TEXT}.pdf"
            )

    @pytest.mark.asyncio
    async def test_ask_file_name(self) -> None:
        self.telegram_update.callback_query = self.telegram_callback_query
        self.telegram_callback_query.edit_message_text.return_value = (
            self.telegram_message
        )

        actual = await self.sut.ask_file_name(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_FILE_NAME
        self.telegram_callback_query.answer.assert_called_once()
        self.telegram_callback_query.edit_message_text.assert_called_once()
        self.telegram_service.cache_message_data.assert_called_once_with(
            self.telegram_context, self.telegram_message
        )

    @pytest.mark.asyncio
    async def test_rename_pdf(self) -> None:
        self.pdf_service.rename_pdf.return_value.__aenter__.return_value = (
            self.FILE_PATH
        )

        actual = await self.sut.rename_pdf(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.pdf_service.rename_pdf.assert_called_once_with(
            self.TELEGRAM_DOCUMENT_ID, f"{self.TELEGRAM_TEXT}.pdf"
        )

    @pytest.mark.asyncio
    async def test_rename_pdf_invalid_file_name(self) -> None:
        self.telegram_message.text = "invalid/file?name"

        actual = await self.sut.rename_pdf(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_FILE_NAME
        self.telegram_update.effective_message.reply_text.assert_called_once()
        self.pdf_service.rename_pdf.assert_not_called()
