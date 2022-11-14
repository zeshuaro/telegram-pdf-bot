from abc import ABC, abstractmethod

from telegram import Update
from telegram.ext import CallbackContext

from pdf_bot.file_processor import AbstractFileProcessor


class AbstractCryptoService(AbstractFileProcessor, ABC):
    @abstractmethod
    def get_wait_password_state(self) -> str:
        pass

    @abstractmethod
    def get_wait_password_text(self) -> str:
        pass

    def should_process_back_option(self) -> bool:
        return True

    def ask_password(self, update: Update, context: CallbackContext) -> str:
        _ = self.language_service.set_app_language(update, context)
        self.telegram_service.reply_with_back_markup(
            update, context, _(self.get_wait_password_text())
        )

        return self.get_wait_password_state()
