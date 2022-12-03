from abc import ABC, abstractmethod

from telegram import Update
from telegram.ext import CallbackContext

from ..abstract_pdf_processor import AbstractPDFProcessor


class AbstractCryptoPDFProcessor(AbstractPDFProcessor, ABC):
    @property
    @abstractmethod
    def wait_password_state(self) -> str:
        pass

    @property
    @abstractmethod
    def wait_password_text(self) -> str:
        pass

    @property
    def should_process_back_option(self) -> bool:
        return True

    def ask_password(self, update: Update, context: CallbackContext) -> str:
        _ = self.language_service.set_app_language(update, context)
        self.telegram_service.reply_with_back_markup(
            update, context, _(self.wait_password_text)
        )

        return self.wait_password_state
