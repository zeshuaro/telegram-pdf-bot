from contextlib import asynccontextmanager
from typing import AsyncGenerator, Type
from unittest.mock import patch

import pytest
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import FILE_DATA
from pdf_bot.file_processor import AbstractFileProcessor, ErrorHandlerType
from pdf_bot.telegram_internal import TelegramUserDataKeyError
from tests.file_task import FileTaskServiceTestMixin
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

    @property
    def task_type(self) -> TaskType:
        return self.TASK_TYPE

    @property
    def should_process_back_option(self) -> bool:
        return True

    @asynccontextmanager
    async def process_file_task(
        self, _file_id: str, _message_text: str
    ) -> AsyncGenerator[str, None]:
        yield self.PROCESS_RESULT


class MockProcessorRaiseGenericErrorWithoutRegisteringGenericError(MockProcessor):
    @asynccontextmanager
    async def process_file_task(
        self, _file_id: str, _password: str
    ) -> AsyncGenerator[str, None]:
        raise GenericError()
        yield self.PROCESS_RESULT  # type: ignore # pylint: disable=unreachable


class MockProcessorWithGenericError(MockProcessor):
    @property
    def generic_error_types(self) -> set[Type[Exception]]:
        return {GenericError}


class MockProcessorRaiseGenericError(MockProcessorWithGenericError):
    @asynccontextmanager
    async def process_file_task(
        self, _file_id: str, _password: str
    ) -> AsyncGenerator[str, None]:
        raise GenericError()
        yield self.PROCESS_RESULT  # type: ignore # pylint: disable=unreachable


class MockProcessorWithCustomErrorHandler(MockProcessor):
    CUSTOM_ERROR_STATE = "custom_error_state"

    @asynccontextmanager
    async def process_file_task(
        self, _file_id: str, _password: str
    ) -> AsyncGenerator[str, None]:
        raise CustomError()
        yield self.PROCESS_RESULT  # type: ignore # pylint: disable=unreachable

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
        _file_id: str,
        _file_name: str,
    ) -> str:
        return self.CUSTOM_ERROR_STATE


class MockProcessorWithUnknownErrorHandler(MockProcessorWithCustomErrorHandler):
    @asynccontextmanager
    async def process_file_task(
        self, _file_id: str, _password: str
    ) -> AsyncGenerator[str, None]:
        raise UnknownError()
        yield self.PROCESS_RESULT  # type: ignore # pylint: disable=unreachable


class MockProcessorWithoutBackOption(MockProcessor):
    @property
    def should_process_back_option(self) -> bool:
        return False


class TestAbstractFileProcessor(
    FileTaskServiceTestMixin,
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    BACK = "Back"

    def setup_method(self) -> None:
        super().setup_method()
        self.file_task_service = self.mock_file_task_service()
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = MockProcessor(
            self.file_task_service,
            self.telegram_service,
            self.language_service,
        )

    @pytest.mark.asyncio
    async def test_process_file(self) -> None:
        actual = await self.sut.process_file(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self._assert_process_file_succeed()

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
            self._assert_process_file_succeed(f"{MockProcessor.PROCESS_RESULT}.zip")
            mock_shutil.make_archive(
                MockProcessor.PROCESS_RESULT, "zip", MockProcessor.PROCESS_RESULT
            )

    @pytest.mark.asyncio
    async def test_process_file_generic_error_not_registered(self) -> None:
        self.sut = MockProcessorRaiseGenericErrorWithoutRegisteringGenericError(
            self.file_task_service,
            self.telegram_service,
            self.language_service,
        )

        actual = await self.sut.process_file(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, FILE_DATA
        )
        self.telegram_update.message.reply_text.assert_not_called()
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_error(self) -> None:
        self.sut = MockProcessorRaiseGenericError(
            self.file_task_service,
            self.telegram_service,
            self.language_service,
        )

        actual = await self.sut.process_file(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, FILE_DATA
        )
        self.telegram_message.reply_text.assert_called_once()
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_custom_error(self) -> None:
        self.sut = MockProcessorWithCustomErrorHandler(
            self.file_task_service,
            self.telegram_service,
            self.language_service,
        )

        actual = await self.sut.process_file(
            self.telegram_update, self.telegram_context
        )

        assert actual == MockProcessorWithCustomErrorHandler.CUSTOM_ERROR_STATE
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, FILE_DATA
        )
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_unknown_error(self) -> None:
        self.sut = MockProcessorWithUnknownErrorHandler(
            self.file_task_service,
            self.telegram_service,
            self.language_service,
        )

        actual = await self.sut.process_file(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, FILE_DATA
        )
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_invalid_user_data(self) -> None:
        self.telegram_service.get_user_data.side_effect = TelegramUserDataKeyError()

        actual = await self.sut.process_file(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, FILE_DATA
        )
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_with_back_option(self) -> None:
        self.telegram_message.text = self.BACK

        actual = await self.sut.process_file(
            self.telegram_update, self.telegram_context
        )

        assert actual == FileTaskServiceTestMixin.WAIT_PDF_TASK
        self.telegram_service.get_user_data.assert_not_called()
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_without_back_option(self) -> None:
        self.sut = MockProcessorWithoutBackOption(
            self.file_task_service,
            self.telegram_service,
            self.language_service,
        )
        self.telegram_message.text = self.BACK

        actual = await self.sut.process_file(
            self.telegram_update, self.telegram_context
        )

        assert actual == ConversationHandler.END
        self._assert_process_file_succeed()

    def _assert_process_file_succeed(
        self, out_path: str = MockProcessor.PROCESS_RESULT
    ) -> None:
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, FILE_DATA
        )
        self.telegram_service.send_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            out_path,
            MockProcessor.TASK_TYPE,
        )
