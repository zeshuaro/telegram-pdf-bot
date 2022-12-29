from unittest.mock import MagicMock

import pytest
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
)

from pdf_bot.analytics import TaskType
from pdf_bot.file_processor import AbstractFileTaskProcessor
from pdf_bot.models import BackData, FileData, TaskData
from pdf_bot.pdf import PdfService
from pdf_bot.pdf.models import ScaleData
from pdf_bot.pdf_processor import (
    ScalePdfData,
    ScalePdfProcessor,
    ScalePdfType,
    ScaleTypeAndValueData,
    ScaleTypeData,
)
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestPdfProcessor(
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    FILE_PATH = "file_path"
    WAIT_SCALE_TYPE = "wait_scale_type"
    WAIT_SCALE_VALUE = "wait_scale_value"
    SCALE_DATA_TEXT = "0.1 0.2"
    SCALE_DATA = ScaleData(0.1, 0.2)

    def setup_method(self) -> None:
        super().setup_method()
        self.scale_pdf_data = ScalePdfData(
            self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_DOCUMENT_NAME
        )
        self.scale_type_data = ScaleTypeData(
            id=self.TELEGRAM_DOCUMENT_ID,
            name=self.TELEGRAM_DOCUMENT_NAME,
            scale_type=ScalePdfType.by_factor,
        )
        self.scale_type_and_value_data = ScaleTypeAndValueData(
            id=self.TELEGRAM_DOCUMENT_ID,
            name=self.TELEGRAM_DOCUMENT_NAME,
            scale_type=ScalePdfType.by_factor,
            scale_value=self.SCALE_DATA,
        )

        self.pdf_service = MagicMock(spec=PdfService)
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = ScalePdfProcessor(
            self.pdf_service,
            self.telegram_service,
            self.language_service,
            bypass_init_check=True,
        )

    def test_task_type(self) -> None:
        actual = self.sut.task_type
        assert actual == TaskType.scale_pdf

    def test_task_data(self) -> None:
        actual = self.sut.task_data
        assert actual == TaskData("Scale", ScalePdfData)

    def test_handler(self) -> None:
        actual = self.sut.handler
        assert isinstance(actual, ConversationHandler)

        entry_points = actual.entry_points
        assert len(entry_points) == 1
        assert isinstance(entry_points[0], CallbackQueryHandler)
        assert entry_points[0].pattern == ScalePdfData

        assert self.WAIT_SCALE_TYPE in actual.states
        wait_scale_type = actual.states[self.WAIT_SCALE_TYPE]
        assert len(wait_scale_type) == 2

        assert isinstance(wait_scale_type[0], CallbackQueryHandler)
        assert wait_scale_type[0].pattern == ScaleTypeData

        assert isinstance(wait_scale_type[1], CallbackQueryHandler)
        assert wait_scale_type[1].pattern == BackData

        assert self.WAIT_SCALE_VALUE in actual.states
        wait_scale_value = actual.states[self.WAIT_SCALE_VALUE]
        assert len(wait_scale_value) == 2

        assert isinstance(wait_scale_value[0], MessageHandler)

        assert isinstance(wait_scale_value[1], CallbackQueryHandler)
        assert wait_scale_value[1].pattern == ScalePdfData

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
    async def test_process_file_task_scale_by_factor(self) -> None:
        file_data = ScaleTypeAndValueData(
            id=self.TELEGRAM_DOCUMENT_ID,
            name=self.TELEGRAM_DOCUMENT_NAME,
            scale_type=ScalePdfType.by_factor,
            scale_value=self.SCALE_DATA,
        )
        self.pdf_service.scale_pdf_by_factor.return_value.__aenter__.return_value = (
            self.FILE_PATH
        )

        async with self.sut.process_file_task(  # pylint: disable=not-async-context-manager
            file_data, self.TELEGRAM_TEXT
        ) as actual:
            assert actual == self.FILE_PATH
            self.pdf_service.scale_pdf_by_factor.assert_called_once_with(
                file_data.id, self.SCALE_DATA
            )

    @pytest.mark.asyncio
    async def test_process_file_task_scale_to_dimension(self) -> None:
        file_data = ScaleTypeAndValueData(
            id=self.TELEGRAM_DOCUMENT_ID,
            name=self.TELEGRAM_DOCUMENT_NAME,
            scale_type=ScalePdfType.to_dimension,
            scale_value=self.SCALE_DATA,
        )
        self.pdf_service.scale_pdf_to_dimension.return_value.__aenter__.return_value = (
            self.FILE_PATH
        )

        async with self.sut.process_file_task(  # pylint: disable=not-async-context-manager
            file_data, self.TELEGRAM_TEXT
        ) as actual:
            assert actual == self.FILE_PATH
            self.pdf_service.scale_pdf_to_dimension.assert_called_once_with(
                file_data.id, self.SCALE_DATA
            )

    @pytest.mark.asyncio
    async def test_process_file_task_invalid_file_data(self) -> None:
        with pytest.raises(TypeError):
            async with self.sut.process_file_task(  # pylint: disable=not-async-context-manager
                self.FILE_DATA, self.TELEGRAM_TEXT
            ) as actual:
                assert actual == self.FILE_PATH
                self.pdf_service.scale_pdf_by_factor.assert_not_called()
                self.pdf_service.scale_pdf_to_dimension.assert_not_called()

    @pytest.mark.asyncio
    async def test_ask_scale_type(self) -> None:
        self.telegram_callback_query.data = self.scale_pdf_data

        actual = await self.sut.ask_scale_type(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_SCALE_TYPE
        self.telegram_callback_query.answer.assert_called_once()
        self.telegram_service.cache_file_data.assert_called_once_with(
            self.telegram_context, self.scale_pdf_data
        )
        self.telegram_callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_scale_type_invalid_callback_query_data(self) -> None:
        self.telegram_callback_query.data = None

        with pytest.raises(TypeError):
            await self.sut.ask_scale_type(self.telegram_update, self.telegram_context)

            self.telegram_callback_query.answer.assert_called_once()
            self.telegram_service.cache_file_data.assert_not_called()
            self.telegram_callback_query.edit_message_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_ask_scale_value(self) -> None:
        self.telegram_callback_query.data = self.scale_type_data
        self.telegram_callback_query.edit_message_text.return_value = (
            self.telegram_message
        )

        actual = await self.sut.ask_scale_value(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_SCALE_VALUE
        self.telegram_callback_query.answer.assert_called_once()
        self.telegram_service.cache_file_data.assert_called_once_with(
            self.telegram_context, self.scale_type_data
        )
        self.telegram_callback_query.edit_message_text.assert_called_once()
        self.telegram_service.cache_message_data.assert_called_once_with(
            self.telegram_context, self.telegram_message
        )

    @pytest.mark.asyncio
    async def test_ask_scale_value_invalid_callback_query_data(self) -> None:
        self.telegram_callback_query.data = None

        with pytest.raises(TypeError):
            await self.sut.ask_scale_value(self.telegram_update, self.telegram_context)

            self.telegram_callback_query.answer.assert_called_once()
            self.telegram_service.cache_file_data.assert_not_called()
            self.telegram_callback_query.edit_message_text.assert_not_called()
            self.telegram_service.cache_message_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_scale_pdf(self) -> None:
        self.telegram_message.text = self.SCALE_DATA_TEXT
        self.telegram_update.callback_query = None
        self.pdf_service.scale_pdf_by_factor.return_value.__enter__.return_value = (
            self.FILE_PATH
        )

        index = 0

        def get_file_data(_context: ContextTypes.DEFAULT_TYPE) -> FileData:
            nonlocal index
            if index == 0:
                index += 1
                return self.scale_type_data
            return self.scale_type_and_value_data

        self.telegram_service.get_file_data.side_effect = get_file_data

        actual = await self.sut.scale_pdf(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        assert self.telegram_service.get_file_data.call_count == 2
        self.telegram_service.cache_file_data.assert_called_once()
        self.pdf_service.scale_pdf_by_factor.assert_called_once()

    @pytest.mark.asyncio
    async def test_scale_pdf_invalid_file_data(self) -> None:
        self.telegram_message.text = self.SCALE_DATA_TEXT
        self.telegram_service.get_file_data.return_value = self.FILE_DATA

        with pytest.raises(TypeError):
            await self.sut.scale_pdf(self.telegram_update, self.telegram_context)

            self.telegram_service.get_file_data.assert_called_once()
            self.telegram_service.cache_file_data.assert_not_called()
            self.pdf_service.scale_pdf_by_factor.assert_not_called()

    @pytest.mark.asyncio
    async def test_scale_pdf_invalid_scale_value(self) -> None:
        self.telegram_message.text = "clearly_invalid"

        actual = await self.sut.scale_pdf(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_SCALE_VALUE
        self.telegram_service.get_file_data.assert_not_called()
        self.telegram_service.cache_file_data.assert_not_called()
        self.pdf_service.scale_pdf_by_factor.assert_not_called()
