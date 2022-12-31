from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator, Callable

from telegram import Update
from telegram.ext import ContextTypes

from pdf_bot.analytics import TaskType
from pdf_bot.file_processor import ErrorHandlerType
from pdf_bot.models import FileData, FileTaskResult, TaskData
from pdf_bot.pdf import PdfIncorrectPasswordError

from .abstract_pdf_text_input_processor import AbstractPdfTextInputProcessor, TextInputData


class DecryptPdfData(FileData):
    pass


class DecryptPdfProcessor(AbstractPdfTextInputProcessor):
    @property
    def task_type(self) -> TaskType:
        return TaskType.decrypt_pdf

    @property
    def entry_point_data_type(self) -> type[DecryptPdfData]:
        return DecryptPdfData

    @property
    def task_data(self) -> TaskData:
        return TaskData(_("Decrypt"), self.entry_point_data_type)

    @property
    def invalid_text_input_error(self) -> str:  # pragma: no cover
        return ""

    def get_ask_text_input_text(self, _: Callable[[str], str]) -> str:  # pragma: no cover
        return _("Send me the password to decrypt your PDF file")

    def get_cleaned_text_input(self, text: str) -> str:
        return text

    @property
    def custom_error_handlers(self) -> dict[type[Exception], ErrorHandlerType]:
        return {PdfIncorrectPasswordError: self._handle_incorrect_password}

    @asynccontextmanager
    async def process_file_task(self, file_data: FileData) -> AsyncGenerator[FileTaskResult, None]:
        if not isinstance(file_data, TextInputData):
            raise TypeError(f"Invalid file data: {type(file_data)}")

        async with self.pdf_service.decrypt_pdf(file_data.id, file_data.text) as path:
            yield FileTaskResult(path)

    async def _handle_incorrect_password(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        exception: Exception,
        file_data: FileData,
    ) -> str:
        _ = self.language_service.set_app_language(update, context)
        await update.effective_message.reply_text(_(str(exception)))  # type: ignore
        self.telegram_service.cache_file_data(context, file_data)
        return self.WAIT_TEXT_INPUT
