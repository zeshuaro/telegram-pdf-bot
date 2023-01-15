from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import ANY, MagicMock, patch

import pytest
from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler

from pdf_bot.analytics import TaskType
from pdf_bot.file_processor import AbstractFileTaskProcessor
from pdf_bot.models import BackData, FileData, FileTaskResult, TaskData
from pdf_bot.pdf import PdfService
from pdf_bot.pdf_processor import (
    AbstractPdfSelectAndTextProcessor,
    OptionAndInputData,
    SelectOption,
    SelectOptionData,
)
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class OptionType(SelectOption):
    a = 0
    b = 1

    @property
    def ask_value_text(self) -> str:
        return f"ask_value_text_{self.value}"


class MockProcessor(AbstractPdfSelectAndTextProcessor):
    CLEANED_TEXT = "cleaned_text"
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

    @property
    def ask_select_option_text(self) -> str:
        return "ask_select_option_text"

    @property
    def select_option_type(self) -> type[OptionType]:
        return OptionType

    @property
    def invalid_text_input_error(self) -> str:
        return "invalid_text_input_error"

    def get_cleaned_text_input(self, _text: str) -> str | None:
        return self.CLEANED_TEXT

    @asynccontextmanager
    async def process_file_task(self, _file_data: FileData) -> AsyncGenerator[FileTaskResult, None]:
        yield self.FILE_TASK_RESULT


class TestAbstractPdfTextInputProcessor(
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    WAIT_SELECT_OPTION = "wait_select_option"
    WAIT_TEXT_INPUT = "wait_text_input"

    def setup_method(self) -> None:
        super().setup_method()

        self.select_option_data = SelectOptionData(
            id=self.TELEGRAM_DOCUMENT_ID,
            name=self.TELEGRAM_DOCUMENT_NAME,
            option=OptionType.a,
        )

        self.option_input_data = OptionAndInputData(
            id=self.TELEGRAM_DOCUMENT_ID,
            name=self.TELEGRAM_DOCUMENT_NAME,
            option=OptionType.a,
            text=MockProcessor.CLEANED_TEXT,
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

        assert self.WAIT_SELECT_OPTION in actual.states
        wait_select_option = actual.states[self.WAIT_SELECT_OPTION]
        assert len(wait_select_option) == 2

        assert isinstance(wait_select_option[0], CallbackQueryHandler)
        assert wait_select_option[0].pattern == SelectOptionData

        assert isinstance(wait_select_option[1], CallbackQueryHandler)
        assert wait_select_option[1].pattern == BackData

        assert self.WAIT_TEXT_INPUT in actual.states
        wait_scale_value = actual.states[self.WAIT_TEXT_INPUT]
        assert len(wait_scale_value) == 2

        assert isinstance(wait_scale_value[0], MessageHandler)

        assert isinstance(wait_scale_value[1], CallbackQueryHandler)
        assert wait_scale_value[1].pattern == self.sut.entry_point_data_type

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
    async def test_ask_select_option(self) -> None:
        actual = await self.sut._ask_select_option(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_SELECT_OPTION
        self.telegram_service.answer_query_and_drop_data.assert_called_once_with(
            self.telegram_context, self.telegram_callback_query
        )
        self.telegram_callback_query.edit_message_text.assert_called_once_with(
            self.sut.ask_select_option_text, reply_markup=ANY
        )

    @pytest.mark.asyncio
    async def test_ask_text_input(self) -> None:
        self.telegram_callback_query.data = self.select_option_data
        self.telegram_callback_query.edit_message_text.return_value = self.telegram_message

        actual = await self.sut._ask_text_input(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_TEXT_INPUT
        self.telegram_service.answer_query_and_drop_data.assert_called_once_with(
            self.telegram_context, self.telegram_callback_query
        )
        self.telegram_callback_query.edit_message_text.assert_called_once_with(
            self.select_option_data.option.ask_value_text,
            reply_markup=ANY,
        )
        self.telegram_service.cache_message_data.assert_called_once_with(
            self.telegram_context, self.telegram_message
        )

    @pytest.mark.asyncio
    async def test_ask_text_input_invalid_callback_query_data(self) -> None:
        self.telegram_callback_query.data = self.FILE_DATA

        with pytest.raises(TypeError):
            await self.sut._ask_text_input(self.telegram_update, self.telegram_context)

        self.telegram_service.answer_query_and_drop_data.assert_called_once_with(
            self.telegram_context, self.telegram_callback_query
        )
        self.telegram_callback_query.edit_message_text.assert_not_called()
        self.telegram_service.cache_message_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_text_input(self) -> None:
        self.telegram_update.callback_query = None

        get_file_data = self.get_file_data_side_effect_by_index(
            self.select_option_data, self.option_input_data
        )
        self.telegram_service.get_file_data.side_effect = get_file_data

        actual = await self.sut._process_text_input(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        assert self.telegram_service.get_file_data.call_count == 2
        self.telegram_service.cache_file_data.assert_called_once_with(
            self.telegram_context, self.option_input_data
        )

    @pytest.mark.asyncio
    async def test_process_text_input_invalid_input(self) -> None:
        with patch.object(self.sut, "get_cleaned_text_input", return_value=None):
            actual = await self.sut._process_text_input(self.telegram_update, self.telegram_context)

            assert actual == self.WAIT_TEXT_INPUT
            self.telegram_service.get_file_data.assert_not_called()
            self.telegram_service.cache_file_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_text_input_invalid_file_data(self) -> None:
        self.telegram_service.get_file_data.return_value = self.FILE_DATA

        with pytest.raises(TypeError):
            await self.sut._process_text_input(self.telegram_update, self.telegram_context)
        self.telegram_service.get_file_data.assert_called_once_with(self.telegram_context)
        self.telegram_service.cache_file_data.assert_not_called()
