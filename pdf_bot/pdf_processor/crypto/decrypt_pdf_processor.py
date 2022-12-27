from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator, Type

from telegram import Update
from telegram.ext import ContextTypes

from pdf_bot.analytics import TaskType
from pdf_bot.consts import FILE_DATA
from pdf_bot.file_processor import ErrorHandlerType
from pdf_bot.models import FileData
from pdf_bot.pdf import PdfIncorrectPasswordError

from .abstract_crypto_pdf_processor import AbstractCryptoPdfProcessor


class DecryptPdfProcessor(AbstractCryptoPdfProcessor):
    @property
    def wait_password_state(self) -> str:
        return "wait_decrypt_password"

    @property
    def wait_password_text(self) -> str:
        return _("Send me the password to decrypt your PDF file")

    @property
    def task_type(self) -> TaskType:
        return TaskType.decrypt_pdf

    @property
    def custom_error_handlers(self) -> dict[Type[Exception], ErrorHandlerType]:
        return {PdfIncorrectPasswordError: self._handle_incorrect_password}

    @asynccontextmanager
    async def process_file_task(
        self, file_data: FileData, message_text: str
    ) -> AsyncGenerator[str, None]:
        async with self.pdf_service.decrypt_pdf(file_data.id, message_text) as path:
            yield path

    async def _handle_incorrect_password(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        exception: Exception,
        file_data: FileData,
    ) -> str:
        _ = self.language_service.set_app_language(update, context)
        await update.effective_message.reply_text(_(str(exception)))  # type: ignore
        context.user_data[FILE_DATA] = file_data  # type: ignore
        return self.wait_password_state
