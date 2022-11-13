import gettext
from contextlib import contextmanager
from typing import ContextManager, Type

from telegram import Update
from telegram.ext import CallbackContext

from pdf_bot.analytics import TaskType
from pdf_bot.consts import PDF_INFO
from pdf_bot.crypto.abstract_crypto_service import (
    AbstractCryptoService,
    ErrorHandlerType,
)
from pdf_bot.pdf import PdfIncorrectPasswordError

_ = gettext.gettext


class DecryptService(AbstractCryptoService):
    def get_wait_password_state(self) -> str:
        return "wait_decrypt_password"

    def get_wait_password_text(self) -> str:
        return _("Send me the password to decrypt your PDF file")

    def get_task_type(self) -> TaskType:
        return TaskType.decrypt_pdf

    def get_custom_error_handlers(self) -> dict[Type[Exception], ErrorHandlerType]:
        return {PdfIncorrectPasswordError: self._handle_incorrect_password}

    @contextmanager
    def process_pdf_task(self, file_id: str, password: str) -> ContextManager[str]:
        with self.pdf_service.decrypt_pdf(file_id, password) as path:
            yield path

    def _handle_incorrect_password(
        self,
        update: Update,
        context: CallbackContext,
        exception: Exception,
        file_id: str,
        file_name: str,
    ) -> str:
        _ = self.language_service.set_app_language(update, context)
        update.effective_message.reply_text(_(str(exception)))
        context.user_data[PDF_INFO] = (file_id, file_name)
        return self.get_wait_password_state()
