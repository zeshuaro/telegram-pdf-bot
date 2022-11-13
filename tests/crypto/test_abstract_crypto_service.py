from contextlib import contextmanager
from typing import ContextManager, Type
from unittest.mock import MagicMock

from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import PDF_INFO
from pdf_bot.crypto import AbstractCryptoService, ErrorHandlerType
from pdf_bot.pdf import PdfService, PdfServiceError
from pdf_bot.telegram import TelegramUserDataKeyError
from tests.file_task import FileTaskServiceTestMixin
from tests.language import LanguageServiceTestMixin
from tests.telegram import TelegramServiceTestMixin, TelegramTestMixin


class MockAbstractCryptoService(AbstractCryptoService):
    STATE = "state"
    TEXT = "text"
    PROCESS_RESULT = "process_result"
    TASK_TYPE = TaskType.decrypt_pdf

    def get_wait_password_state(self) -> str:
        return MockAbstractCryptoService.STATE

    def get_wait_password_text(self) -> str:
        return MockAbstractCryptoService.TEXT

    def get_task_type(self) -> TaskType:
        return MockAbstractCryptoService.TASK_TYPE

    @contextmanager
    def process_pdf_task(self, _file_id: str, _password: str) -> ContextManager[str]:
        yield self.PROCESS_RESULT


class MockAbstractCryptoServiceWithPDFServiceError(MockAbstractCryptoService):
    @contextmanager
    def process_pdf_task(self, _file_id: str, _password: str) -> ContextManager[str]:
        raise PdfServiceError()


class MockAbstractCryptoServiceWithCustomError(MockAbstractCryptoService):
    @contextmanager
    def process_pdf_task(self, _file_id: str, _password: str) -> ContextManager[str]:
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
        return self.get_wait_password_state()


class MockAbstractCryptoServiceWithUnknownError(MockAbstractCryptoService):
    @contextmanager
    def process_pdf_task(self, _file_id: str, _password: str) -> ContextManager[str]:
        raise RuntimeError()


class TestAbstractCryptoService(
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

        self.sut = MockAbstractCryptoService(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

    def test_ask_password(self) -> None:
        actual = self.sut.ask_password(self.telegram_update, self.telegram_context)
        assert actual == MockAbstractCryptoService.STATE
        self.telegram_service.reply_with_back_markup.assert_called_once()

    def test_process_pdf(self) -> None:
        actual = self.sut.process_pdf(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, PDF_INFO
        )
        self.telegram_service.reply_with_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            MockAbstractCryptoService.PROCESS_RESULT,
            MockAbstractCryptoService.TASK_TYPE,
        )

    def test_process_pdf_error(self) -> None:
        self.sut = MockAbstractCryptoServiceWithPDFServiceError(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

        actual = self.sut.process_pdf(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, PDF_INFO
        )
        self.telegram_message.reply_text.assert_called_once()
        self.telegram_service.reply_with_file.assert_not_called()

    def test_process_pdf_custom_error(self) -> None:
        self.sut = MockAbstractCryptoServiceWithCustomError(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

        actual = self.sut.process_pdf(self.telegram_update, self.telegram_context)

        assert actual == MockAbstractCryptoServiceWithCustomError.STATE
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, PDF_INFO
        )
        self.telegram_service.reply_with_file.assert_not_called()

    def test_process_pdf_unknown_error(self) -> None:
        self.sut = MockAbstractCryptoServiceWithUnknownError(
            self.file_task_service,
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

        actual = self.sut.process_pdf(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, PDF_INFO
        )
        self.telegram_service.reply_with_file.assert_not_called()

    def test_process_pdf_invalid_user_data(self) -> None:
        self.telegram_service.get_user_data.side_effect = TelegramUserDataKeyError()

        actual = self.sut.process_pdf(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, PDF_INFO
        )
        self.telegram_service.reply_with_file.assert_not_called()

    def test_process_pdf_back(self) -> None:
        self.telegram_message.text = self.BACK

        actual = self.sut.process_pdf(self.telegram_update, self.telegram_context)

        assert actual == FileTaskServiceTestMixin.WAIT_PDF_TASK
        self.telegram_service.get_user_data.assert_not_called()
        self.telegram_service.reply_with_file.assert_not_called()
