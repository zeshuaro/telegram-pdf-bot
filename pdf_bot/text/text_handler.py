from telegram.ext import (
    BaseHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
)

from pdf_bot.consts import TEXT_FILTER
from pdf_bot.telegram_handler import AbstractTelegramHandler
from pdf_bot.telegram_internal import TelegramService

from .text_service import TextService


class TextHandler(AbstractTelegramHandler):
    _TEXT_COMMAND = "text"

    def __init__(self, text_service: TextService, telegram_service: TelegramService) -> None:
        self.text_service = text_service
        self.telegram_service = telegram_service

    @property
    def handlers(self) -> list[BaseHandler]:
        return [
            ConversationHandler(
                entry_points=[CommandHandler(self._TEXT_COMMAND, self.text_service.ask_pdf_text)],
                states={
                    TextService.WAIT_TEXT: [
                        MessageHandler(TEXT_FILTER, self.text_service.ask_pdf_font)
                    ],
                    TextService.WAIT_FONT: [
                        MessageHandler(TEXT_FILTER, self.text_service.check_text)
                    ],
                },
                fallbacks=[
                    CommandHandler("cancel", self.telegram_service.cancel_conversation),
                ],
                allow_reentry=True,
            )
        ]
