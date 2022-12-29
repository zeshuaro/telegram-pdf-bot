from telegram.ext import BaseHandler, CallbackQueryHandler, CommandHandler

from pdf_bot.telegram_handler import AbstractTelegramHandler

from .language_service import LanguageService
from .models import LanguageData, SetLanguageData


class LanguageHandler(AbstractTelegramHandler):
    _SET_LANGUAGE_COMMAND = "setlang"

    def __init__(self, language_service: LanguageService) -> None:
        self.language_service = language_service

    @property
    def handlers(self) -> list[BaseHandler]:
        return [
            CommandHandler(
                self._SET_LANGUAGE_COMMAND, self.language_service.send_language_options
            ),
            CallbackQueryHandler(
                self.language_service.send_language_options, pattern=SetLanguageData
            ),
            CallbackQueryHandler(
                self.language_service.update_user_language, pattern=LanguageData
            ),
        ]
