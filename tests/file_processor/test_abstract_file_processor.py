from contextlib import asynccontextmanager
from typing import AsyncGenerator, Type
from unittest.mock import MagicMock, patch

import pytest
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import BaseHandler, ContextTypes, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.file_processor import AbstractFileProcessor, ErrorHandlerType
from pdf_bot.models import FileData, FileTaskResult, TaskData
from pdf_bot.telegram_internal import TelegramGetUserDataError
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class GenericError(Exception):
    pass


class CustomError(Exception):
    pass


class UnknownError(Exception):
    pass


class MockProcessor(AbstractFileProcessor):
    PROCESS_RESULT = "process_result"
    TASK_TYPE = TaskType.decrypt_pdf
    TASK_DATA_LIST = [TaskData("a", FileData), TaskData("b", FileData)]
    FILE_TASK_RESULT = FileTaskResult("path")

    @classmethod
    def get_task_data_list(cls) -> list[TaskData]:
        return cls.TASK_DATA_LIST

    @property
    def task_type(self) -> TaskType:
        return self.TASK_TYPE

    @property
    def task_data(self) -> TaskData:
        return MagicMock(spec=TaskData)

    @property
    def handler(self) -> BaseHandler:
        return MagicMock(spec=BaseHandler)

    @asynccontextmanager
    async def process_file_task(
        self, _file_data: FileData
    ) -> AsyncGenerator[FileTaskResult, None]:
        yield self.FILE_TASK_RESULT


class MockProcessorWithGenericError(MockProcessor):
    @property
    def generic_error_types(self) -> set[Type[Exception]]:
        return {GenericError}


class MockProcessorWithCustomErrorHandler(MockProcessor):
    CUSTOM_ERROR_STATE = "custom_error_state"

    @property
    def custom_error_handlers(
        self,
    ) -> dict[Type[Exception], ErrorHandlerType]:
        return {CustomError: self._handle_custom_error}

    async def _handle_custom_error(
        self,
        _update: Update,
        _context: ContextTypes.DEFAULT_TYPE,
        _exception: Exception,
        _file_data: FileData,
    ) -> str:
        return self.CUSTOM_ERROR_STATE


class TestAbstractFileProcessor(
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    BACK = "Back"
    WAIT_FILE_TASK = "wait_file_task"

    def setup_method(self) -> None:
        super().setup_method()
        self.telegram_update.callback_query = None

        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = MockProcessor(
            self.telegram_service,
            self.language_service,
            bypass_init_check=True,
        )

    @pytest.mark.asyncio
    async def test_ask_task(self) -> None:
        self.telegram_update.callback_query = self.telegram_callback_query

        with patch.object(
            self.sut, "ask_task_helper", return_value=self.WAIT_FILE_TASK
        ) as ask_task_helper:
            actual = await self.sut.ask_task(
                self.telegram_update, self.telegram_context
            )

            assert actual == self.WAIT_FILE_TASK
            self.telegram_callback_query.delete_message.assert_called_once()
            ask_task_helper.assert_called_once_with(
                self.language_service,
                self.telegram_update,
                self.telegram_context,
                MockProcessor.TASK_DATA_LIST,
            )

    @pytest.mark.asyncio
    async def test_ask_task_without_callback_query(self) -> None:
        self.telegram_update.callback_query = None

        with patch.object(
            self.sut, "ask_task_helper", return_value=self.WAIT_FILE_TASK
        ) as ask_task_helper:
            actual = await self.sut.ask_task(
                self.telegram_update, self.telegram_context
            )

            assert actual == self.WAIT_FILE_TASK
            self.telegram_callback_query.delete_message.assert_not_called()
            ask_task_helper.assert_called_once_with(
                self.language_service,
                self.telegram_update,
                self.telegram_context,
                MockProcessor.TASK_DATA_LIST,
            )

    @pytest.mark.asyncio
    async def test_process_file(self) -> None:
        actual = await self.sut.process_file(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self._assert_process_file_succeed()

    @pytest.mark.asyncio
    async def test_process_file_with_result_message(self) -> None:
        with patch.object(
            self.sut,
            "process_file_task",
        ) as process_file_task:
            process_file_task.return_value.__aenter__.return_value = FileTaskResult(
                MockProcessor.FILE_TASK_RESULT.path, self.TELEGRAM_TEXT
            )

            actual = await self.sut.process_file(
                self.telegram_update, self.telegram_context
            )

            assert actual == ConversationHandler.END
            self._assert_process_file_succeed()
            self.telegram_service.send_message.assert_called_once_with(
                self.telegram_update, self.telegram_context, self.TELEGRAM_TEXT
            )

    @pytest.mark.asyncio
    async def test_process_file_dir_output(self) -> None:
        with patch(
            "pdf_bot.file_processor.abstract_file_processor.os"
        ) as mock_os, patch(
            "pdf_bot.file_processor.abstract_file_processor.shutil"
        ) as mock_shutil:
            mock_os.path.is_dir.return_value = True

            actual = await self.sut.process_file(
                self.telegram_update, self.telegram_context
            )

            assert actual == ConversationHandler.END
            self._assert_process_file_succeed(
                f"{MockProcessor.FILE_TASK_RESULT.path}.zip"
            )
            mock_shutil.make_archive(
                MockProcessor.PROCESS_RESULT, "zip", MockProcessor.PROCESS_RESULT
            )

    @pytest.mark.asyncio
    async def test_process_file_generic_error_not_registered(self) -> None:
        with patch.object(
            self.sut, "process_file_task", side_effect=GenericError
        ), pytest.raises(GenericError):
            await self.sut.process_file(self.telegram_update, self.telegram_context)

        self._assert_get_file_and_messsage_data()
        self.telegram_update.effective_message.reply_text.assert_not_called()
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_error(self) -> None:
        sut = MockProcessorWithGenericError(
            self.telegram_service, self.language_service, bypass_init_check=True
        )

        with patch.object(sut, "process_file_task", side_effect=GenericError):
            actual = await sut.process_file(self.telegram_update, self.telegram_context)

            assert actual == ConversationHandler.END
            self._assert_get_file_and_messsage_data()
            self.telegram_message.reply_text.assert_called_once()
            self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_custom_error(self) -> None:
        sut = MockProcessorWithCustomErrorHandler(
            self.telegram_service, self.language_service, bypass_init_check=True
        )

        with patch.object(sut, "process_file_task", side_effect=CustomError):
            actual = await sut.process_file(self.telegram_update, self.telegram_context)

            assert actual == MockProcessorWithCustomErrorHandler.CUSTOM_ERROR_STATE
            self._assert_get_file_and_messsage_data()
            self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_unknown_error(self) -> None:
        sut = MockProcessorWithCustomErrorHandler(
            self.telegram_service, self.language_service, bypass_init_check=True
        )

        with patch.object(
            sut, "process_file_task", side_effect=UnknownError
        ), pytest.raises(UnknownError):
            await sut.process_file(self.telegram_update, self.telegram_context)

        self._assert_get_file_and_messsage_data()
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_invalid_file_data(self) -> None:
        self.telegram_service.get_file_data.side_effect = TelegramGetUserDataError()

        actual = await self.sut.process_file(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self.telegram_service.get_file_data.assert_called_once_with(
            self.telegram_context
        )
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_with_callback_query(self) -> None:
        self.telegram_callback_query.data = self.FILE_DATA
        self.telegram_update.callback_query = self.telegram_callback_query

        actual = await self.sut.process_file(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self.telegram_service.answer_query_and_drop_data.assert_called_once_with(
            self.telegram_context, self.telegram_callback_query
        )
        self.telegram_service.send_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            MockProcessor.FILE_TASK_RESULT.path,
            MockProcessor.TASK_TYPE,
        )

    @pytest.mark.asyncio
    async def test_process_file_with_callback_query_unknown_data(self) -> None:
        self.telegram_callback_query.data = None
        self.telegram_update.callback_query = self.telegram_callback_query

        with pytest.raises(ValueError):
            await self.sut.process_file(self.telegram_update, self.telegram_context)
            self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("error", [TelegramGetUserDataError, BadRequest("Error")])
    async def test_process_file_process_previous_message_error(
        self, error: Exception
    ) -> None:
        self.telegram_service.get_message_data.side_effect = error

        actual = await self.sut.process_file(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self._assert_process_file_succeed()
        self.telegram_context.bot.delete_message.assert_not_called()

    def _assert_process_file_succeed(
        self, out_path: str = MockProcessor.FILE_TASK_RESULT.path
    ) -> None:
        self._assert_get_file_and_messsage_data()
        self.telegram_service.send_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            out_path,
            MockProcessor.TASK_TYPE,
        )

    def _assert_get_file_and_messsage_data(self) -> None:
        self.telegram_service.get_file_data.assert_called_once_with(
            self.telegram_context
        )
        self.telegram_service.get_message_data.assert_called_once_with(
            self.telegram_context
        )
