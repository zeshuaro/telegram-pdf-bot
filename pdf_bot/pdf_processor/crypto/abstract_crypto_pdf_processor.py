from abc import ABC, abstractmethod

from telegram import Update
from telegram.ext import ContextTypes

from ..abstract_pdf_processor import AbstractPdfProcessor


class AbstractCryptoPdfProcessor(AbstractPdfProcessor, ABC):
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

    async def ask_password(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        _ = self.language_service.set_app_language(update, context)
        await self.telegram_service.reply_with_back_markup(
            update, context, _(self.wait_password_text)
        )

        return self.wait_password_state
