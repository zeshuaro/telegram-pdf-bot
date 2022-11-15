from contextlib import contextmanager
from typing import Generator, Type
from unittest.mock import MagicMock

from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import PDF_INFO
from pdf_bot.file_processor import AbstractFileProcessor, ErrorHandlerType
from pdf_bot.pdf import PdfService, PdfServiceError
from pdf_bot.telegram_internal import TelegramUserDataKeyError
from tests.file_task import FileTaskServiceTestMixin
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class MockProcessor(AbstractFileProcessor):
    PROCESS_RESULT = "process_result"
    TASK_TYPE = TaskType.decrypt_pdf

    @property
    def task_type(self) -> TaskType:
        return self.TASK_TYPE

    @property
    def should_process_back_option(self) -> bool:
        return True

    @contextmanager
    def process_file_task(
        self, _file_id: str, _message_text: str
    ) -> Generator[str, None, None]:
        yield self.PROCESS_RESULT


class MockProcessorWithPDFServiceError(MockProcessor):
    @contextmanager
    def process_file_task(
        self, _file_id: str, _password: str
    ) -> Generator[str, None, None]:
        raise PdfServiceError()


class MockProcessorWithErrorHandler(MockProcessor):
    CUSTOM_ERROR_STATE = "custom_error_state"

    @contextmanager
    def process_file_task(
        self, _file_id: str, _password: str
    ) -> Generator[str, None, None]:
        raise RuntimeError()

    def get_custom_error_handlers(
        self,
    ) -> dict[Type[Exception], ErrorHandlerType]:
        return {RuntimeError: self._handle_runtime_error}

    def _handle_runtime_error(
        self,
        _update: Update,
        _context: CallbackContext,
        _exception: Exception,
        _file_id: str,
        _file_name: str,
    ) -> str:
        return self.CUSTOM_ERROR_STATE


class MockProcessorWithoutErrorHandler(MockProcessor):
    @contextmanager
    def process_file_task(
        self, _file_id: str, _password: str
    ) -> Generator[str, None, None]:
        raise RuntimeError()


class MockProcessorWithoutBackOption(MockProcessor):
    @property
    def should_process_back_option(self) -> bool:
        return False


class TestAbstractTelegramFileProcessor(
    FileTaskServiceTestMixin,
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    WAIT_DECRYPT_PASSWORD = "wait_decrypt_password"
    FILE_PATH = "file_path"
    BACK = "Back"

    def setup_method(self) -> None:
        super().setup_method()
        self.pdf_service = MagicMock(spec=PdfService)
        self.file_task_service = self.mock_file_task_service()
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = MockProcessor(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

    def test_process_file(self) -> None:
        actual = self.sut.process_file(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self._assert_process_file_succeed()

    def test_process_file_error(self) -> None:
        self.sut = MockProcessorWithPDFServiceError(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

        actual = self.sut.process_file(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, PDF_INFO
        )
        self.telegram_message.reply_text.assert_called_once()
        self.telegram_service.reply_with_file.assert_not_called()

    def test_process_file_custom_error(self) -> None:
        self.sut = MockProcessorWithErrorHandler(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

        actual = self.sut.process_file(self.telegram_update, self.telegram_context)

        assert actual == MockProcessorWithErrorHandler.CUSTOM_ERROR_STATE
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, PDF_INFO
        )
        self.telegram_service.reply_with_file.assert_not_called()

    def test_process_file_unknown_error(self) -> None:
        self.sut = MockProcessorWithoutErrorHandler(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

        actual = self.sut.process_file(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, PDF_INFO
        )
        self.telegram_service.reply_with_file.assert_not_called()

    def test_process_file_invalid_user_data(self) -> None:
        self.telegram_service.get_user_data.side_effect = TelegramUserDataKeyError()

        actual = self.sut.process_file(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, PDF_INFO
        )
        self.telegram_service.reply_with_file.assert_not_called()

    def test_process_file_with_back_option(self) -> None:
        self.telegram_message.text = self.BACK

        actual = self.sut.process_file(self.telegram_update, self.telegram_context)

        assert actual == FileTaskServiceTestMixin.WAIT_PDF_TASK
        self.telegram_service.get_user_data.assert_not_called()
        self.telegram_service.reply_with_file.assert_not_called()

    def test_process_file_without_back_option(self) -> None:
        self.sut = MockProcessorWithoutBackOption(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )
        self.telegram_message.text = self.BACK

        actual = self.sut.process_file(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self._assert_process_file_succeed()

    def _assert_process_file_succeed(self) -> None:
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, PDF_INFO
        )
        self.telegram_service.reply_with_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            MockProcessor.PROCESS_RESULT,
            MockProcessor.TASK_TYPE,
        )
