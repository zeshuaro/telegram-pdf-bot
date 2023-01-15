from unittest.mock import MagicMock

import pytest
from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.file_processor import AbstractFileTaskProcessor
from pdf_bot.models import BackData, TaskData
from pdf_bot.pdf import PdfService
from pdf_bot.pdf_processor import RotateDegreeData, RotatePdfData, RotatePdfProcessor
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestRotatePdfProcessor(
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):

    WAIT_DEGREE = "wait_degree"

    def setup_method(self) -> None:
        super().setup_method()
        self.telegram_update.callback_query = None

        self.pdf_service = MagicMock(spec=PdfService)
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = RotatePdfProcessor(
            self.pdf_service,
            self.telegram_service,
            self.language_service,
            bypass_init_check=True,
        )

    def test_task_type(self) -> None:
        actual = self.sut.task_type
        assert actual == TaskType.rotate_pdf

    def test_task_data(self) -> None:
        actual = self.sut.task_data
        assert actual == TaskData("Rotate", RotatePdfData)

    def test_handler(self) -> None:
        actual = self.sut.handler
        assert isinstance(actual, ConversationHandler)

        entry_points = actual.entry_points
        assert len(entry_points) == 1
        assert isinstance(entry_points[0], CallbackQueryHandler)
        assert entry_points[0].pattern == RotatePdfData

        assert self.WAIT_DEGREE in actual.states
        wait_degree_state = actual.states[self.WAIT_DEGREE]
        assert len(wait_degree_state) == 2

        assert isinstance(wait_degree_state[0], CallbackQueryHandler)
        assert wait_degree_state[0].pattern == RotateDegreeData

        assert isinstance(wait_degree_state[1], CallbackQueryHandler)
        assert wait_degree_state[1].pattern == BackData

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
        degree = 90
        degree_data = RotateDegreeData(
            id=self.TELEGRAM_DOCUMENT_ID,
            name=self.TELEGRAM_DOCUMENT_NAME,
            degree=degree,
        )
        self.pdf_service.rotate_pdf.return_value.__aenter__.return_value = self.FILE_PATH

        async with self.sut.process_file_task(degree_data) as actual:
            assert actual == self.FILE_TASK_RESULT
            self.pdf_service.rotate_pdf.assert_called_once_with(degree_data.id, degree)

    @pytest.mark.asyncio
    async def test_process_file_task_invalid_file_data(self) -> None:
        with pytest.raises(TypeError):
            async with self.sut.process_file_task(self.FILE_DATA):
                pass
        self.pdf_service.rotate_pdf.assert_not_called()

    @pytest.mark.asyncio
    async def test_ask_degree(self) -> None:
        self.telegram_callback_query.data = RotatePdfData(
            self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_DOCUMENT_NAME
        )
        self.telegram_update.callback_query = self.telegram_callback_query

        actual = await self.sut.ask_degree(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_DEGREE
        self.telegram_service.answer_query_and_drop_data.assert_called_once_with(
            self.telegram_context, self.telegram_callback_query
        )
        self.telegram_callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_degree_invalid_callback_query_data(self) -> None:
        self.telegram_update.callback_query = self.telegram_callback_query

        with pytest.raises(TypeError):
            await self.sut.ask_degree(self.telegram_update, self.telegram_context)
        self.telegram_service.answer_query_and_drop_data.assert_called_once_with(
            self.telegram_context, self.telegram_callback_query
        )
        self.telegram_callback_query.edit_message_text.assert_not_called()
