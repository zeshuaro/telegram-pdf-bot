from telegram.ext import BaseHandler, CallbackQueryHandler

from pdf_bot.telegram_handler import AbstractTelegramHandler

from .error_service import ErrorService


class ErrorCallbackQueryHandler(AbstractTelegramHandler):
    def __init__(self, error_service: ErrorService) -> None:
        self.error_service = error_service

    @property
    def handlers(self) -> list[BaseHandler]:
        return [CallbackQueryHandler(self.error_service.process_unknown_callback_query)]
