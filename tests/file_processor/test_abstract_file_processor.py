from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import BaseHandler, ContextTypes, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.errors import CallbackQueryDataTypeError
from pdf_bot.file_processor import AbstractFileProcessor, ErrorHandlerType
from pdf_bot.file_processor.errors import DuplicateClassError
from pdf_bot.language import LanguageService
from pdf_bot.models import FileData, FileTaskResult, TaskData
from pdf_bot.telegram_internal import TelegramGetUserDataError, TelegramService
from tests.language import LanguageServiceTestMixin
from tests.path_test_mixin import PathTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class GenericError(Exception):
    pass


class CustomError(Exception):
    pass


class UnknownError(Exception):
    pass


class MockProcessor(PathTestMixin, AbstractFileProcessor):
    PROCESS_RESULT = "process_result"
    TASK_TYPE = TaskType.decrypt_pdf
    TASK_DATA_LIST = (TaskData("a", FileData), TaskData("b", FileData))

    def __init__(
        self,
        telegram_service: TelegramService,
        language_service: LanguageService,
        bypass_init_check: bool = False,
    ) -> None:
        super().__init__(telegram_service, language_service, bypass_init_check)
        self.path = self.mock_file_path()
        self.file_task_result = FileTaskResult(self.path)

    @classmethod
    def get_task_data_list(cls) -> Sequence[TaskData]:
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
    async def process_file_task(self, _file_data: FileData) -> AsyncGenerator[FileTaskResult, None]:
        yield self.file_task_result


class MockProcessorWithGenericError(MockProcessor):
    @property
    def generic_error_types(self) -> set[type[Exception]]:
        return {GenericError}


class MockProcessorWithCustomErrorHandler(MockProcessor):
    CUSTOM_ERROR_STATE = "custom_error_state"

    @property
    def custom_error_handlers(
        self,
    ) -> dict[type[Exception], ErrorHandlerType]:
        return {CustomError: self._handle_custom_error}

    async def _handle_custom_error(
        self,
        _update: Update,
        _context: ContextTypes.DEFAULT_TYPE,
        _exception: Exception,
        _file_data: FileData,
    ) -> str:
        return self.CUSTOM_ERROR_STATE


class TestAbstractFileProcessorInit(
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
):
    def setup_method(self) -> None:
        super().setup_method()
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.file_processors_patcher = patch(
            "pdf_bot.file_processor.abstract_file_processor.AbstractFileProcessor._FILE_PROCESSORS"
        )
        self.file_processors = self.file_processors_patcher.start()

    def teardown_method(self) -> None:
        self.file_processors_patcher.stop()
        super().teardown_method()

    def test_init(self) -> None:
        processors: dict = {}
        self.file_processors.__contains__.side_effect = processors.__contains__

        proc = MockProcessor(self.telegram_service, self.language_service)

        self.file_processors.__setitem__.assert_called_once_with(proc.__class__.__name__, proc)

    def test_init_already_initialized(self) -> None:
        processors: dict = {MockProcessor.__name__: MagicMock()}
        self.file_processors.__contains__.side_effect = processors.__contains__

        with pytest.raises(DuplicateClassError):
            MockProcessor(self.telegram_service, self.language_service)

        self.file_processors.__setitem__.assert_not_called()


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
            actual = await self.sut.ask_task(self.telegram_update, self.telegram_context)

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
            actual = await self.sut.ask_task(self.telegram_update, self.telegram_context)

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
        actual = await self.sut.process_file(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self._assert_process_file_succeed()

    @pytest.mark.asyncio
    async def test_process_file_with_result_message(self) -> None:
        with patch.object(self.sut, "process_file_task") as process_file_task:
            result = FileTaskResult(self.sut.path, self.TELEGRAM_TEXT)
            process_file_task.return_value.__aenter__.return_value = result

            actual = await self.sut.process_file(self.telegram_update, self.telegram_context)

            assert actual == ConversationHandler.END
            self._assert_process_file_succeed()
            self.telegram_service.send_message.assert_called_once_with(
                self.telegram_update, self.telegram_context, self.TELEGRAM_TEXT
            )

    @pytest.mark.asyncio
    async def test_process_file_dir_output(self) -> None:
        with (
            patch.object(self.sut, "process_file_task") as process_file_task,
            patch("pdf_bot.file_processor.abstract_file_processor.shutil") as mock_shutil,
        ):
            path_with_suffix = self.mock_file_path()
            dir_path = self.mock_dir_path()
            dir_path.with_suffix.return_value = path_with_suffix

            result = FileTaskResult(dir_path, self.TELEGRAM_TEXT)
            process_file_task.return_value.__aenter__.return_value = result

            actual = await self.sut.process_file(self.telegram_update, self.telegram_context)

            assert actual == ConversationHandler.END
            self._assert_process_file_succeed(path_with_suffix)
            dir_path.with_suffix.assert_called_once_with(".zip")
            mock_shutil.make_archive(
                MockProcessor.PROCESS_RESULT, "zip", MockProcessor.PROCESS_RESULT
            )

    @pytest.mark.asyncio
    async def test_process_file_generic_error_not_registered(self) -> None:
        with (
            patch.object(self.sut, "process_file_task", side_effect=GenericError),
            pytest.raises(GenericError),
        ):
            await self.sut.process_file(self.telegram_update, self.telegram_context)

        self._assert_get_file_and_message_data()
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
            self._assert_get_file_and_message_data()
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
            self._assert_get_file_and_message_data()
            self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_unknown_error(self) -> None:
        sut = MockProcessorWithCustomErrorHandler(
            self.telegram_service, self.language_service, bypass_init_check=True
        )

        with (
            patch.object(sut, "process_file_task", side_effect=UnknownError),
            pytest.raises(UnknownError),
        ):
            await sut.process_file(self.telegram_update, self.telegram_context)

        self._assert_get_file_and_message_data()
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_invalid_file_data(self) -> None:
        self.telegram_service.get_file_data.side_effect = TelegramGetUserDataError()

        actual = await self.sut.process_file(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.get_file_data.assert_called_once_with(self.telegram_context)
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_with_callback_query(self) -> None:
        self.telegram_callback_query.data = self.FILE_DATA
        self.telegram_update.callback_query = self.telegram_callback_query

        actual = await self.sut.process_file(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.answer_query_and_drop_data.assert_called_once_with(
            self.telegram_context, self.telegram_callback_query
        )
        self.telegram_service.send_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            self.sut.path,
            MockProcessor.TASK_TYPE,
        )

    @pytest.mark.asyncio
    async def test_process_file_with_callback_query_unknown_data(self) -> None:
        self.telegram_callback_query.data = None
        self.telegram_update.callback_query = self.telegram_callback_query

        with pytest.raises(CallbackQueryDataTypeError):
            await self.sut.process_file(self.telegram_update, self.telegram_context)

        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("error", [TelegramGetUserDataError, BadRequest("Error")])
    async def test_process_file_process_previous_message_error(self, error: Exception) -> None:
        self.telegram_service.get_message_data.side_effect = error

        actual = await self.sut.process_file(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self._assert_process_file_succeed()
        self.telegram_context.bot.delete_message.assert_not_called()

    def _assert_process_file_succeed(self, path: Path | None = None) -> None:
        if path is None:
            path = self.sut.path

        self._assert_get_file_and_message_data()
        self.telegram_service.send_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            path,
            MockProcessor.TASK_TYPE,
        )

    def _assert_get_file_and_message_data(self) -> None:
        self.telegram_service.get_file_data.assert_called_once_with(self.telegram_context)
        self.telegram_service.get_message_data.assert_called_once_with(self.telegram_context)
