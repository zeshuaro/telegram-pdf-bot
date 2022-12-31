from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable
from unittest.mock import MagicMock, patch

import pytest
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
)

from pdf_bot.analytics import TaskType
from pdf_bot.file_processor import AbstractFileTaskProcessor
from pdf_bot.models import BackData, FileData, FileTaskResult, TaskData
from pdf_bot.pdf import PdfService
from pdf_bot.pdf_processor import AbstractPdfTextInputProcessor, TextInputData
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class MockProcessor(AbstractPdfTextInputProcessor):
    FILE_NAME = "file_name"
    FILE_TASK_RESULT = FileTaskResult("path")

    @property
    def entry_point_data_type(self) -> type[FileData]:
        return FileData

    @property
    def task_type(self) -> TaskType:
        return TaskType.decrypt_pdf

    @property
    def task_data(self) -> TaskData:
        return MagicMock(spec=TaskData)

    def get_ask_text_input_text(self, _: Callable[[str], str]) -> str:
        return "ask_text_input_text"

    @property
    def invalid_text_input_error(self) -> str:
        return "invalid_text_input_error"

    def get_cleaned_text_input(self, _text: str) -> str | None:
        return self.FILE_NAME

    @asynccontextmanager
    async def process_file_task(self, _file_data: FileData) -> AsyncGenerator[FileTaskResult, None]:
        yield self.FILE_TASK_RESULT


class TestAbstractPdfTextInputProcessor(
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    WAIT_TEXT_INPUT = "wait_text_input"

    def setup_method(self) -> None:
        super().setup_method()

        self.text_input_data = TextInputData(
            id=self.TELEGRAM_DOCUMENT_ID,
            name=self.TELEGRAM_DOCUMENT_NAME,
            text=MockProcessor.FILE_NAME,
        )

        self.pdf_service = MagicMock(spec=PdfService)
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = MockProcessor(
            self.pdf_service,
            self.telegram_service,
            self.language_service,
            bypass_init_check=True,
        )

    def test_handler(self) -> None:
        actual = self.sut.handler

        assert isinstance(actual, ConversationHandler)

        entry_points = actual.entry_points
        assert len(entry_points) == 1
        assert isinstance(entry_points[0], CallbackQueryHandler)
        assert entry_points[0].pattern == self.sut.entry_point_data_type

        assert self.WAIT_TEXT_INPUT in actual.states
        wait_file_name_state = actual.states[self.WAIT_TEXT_INPUT]
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
    async def test_ask_text_input(self) -> None:
        self.telegram_callback_query.edit_message_text.return_value = self.telegram_message

        actual = await self.sut._ask_text_input(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_TEXT_INPUT
        self.telegram_service.answer_query_and_drop_data.assert_called_once_with(
            self.telegram_context, self.telegram_callback_query
        )
        self.telegram_callback_query.edit_message_text.assert_called_once_with(
            self.sut.get_ask_text_input_text(self.language_service.set_app_language()),
            parse_mode=ParseMode.HTML,
            reply_markup=self.BACK_INLINE_MARKUP,
        )
        self.telegram_service.cache_message_data.assert_called_once_with(
            self.telegram_context, self.telegram_message
        )

    @pytest.mark.asyncio
    async def test_process_text_input(self) -> None:
        self.telegram_update.callback_query = None

        get_file_data = self.get_file_data_side_effect_by_index(
            self.FILE_DATA, self.text_input_data
        )
        self.telegram_service.get_file_data.side_effect = get_file_data

        actual = await self.sut._process_text_input(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        assert self.telegram_service.get_file_data.call_count == 2
        self.telegram_service.cache_file_data.assert_called_once_with(
            self.telegram_context, self.text_input_data
        )

    @pytest.mark.asyncio
    async def test_process_text_input_invalid_input(self) -> None:
        with patch.object(self.sut, "get_cleaned_text_input", return_value=None):
            actual = await self.sut._process_text_input(self.telegram_update, self.telegram_context)

            assert actual == self.WAIT_TEXT_INPUT
            self.telegram_service.get_file_data.assert_not_called()
            self.telegram_service.cache_file_data.assert_not_called()
