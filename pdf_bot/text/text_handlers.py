from telegram.ext import CommandHandler, ConversationHandler, MessageHandler

from pdf_bot.consts import TEXT_FILTER
from pdf_bot.text.constants import WAIT_FONT, WAIT_TEXT
from pdf_bot.text.text_service import TextService
from pdf_bot.utils import cancel


class TextHandlers:
    def __init__(self, text_service: TextService) -> None:
        self.text_service = text_service

    def conversation_handler(self):
        return ConversationHandler(
            entry_points=[CommandHandler("text", self.text_service.ask_pdf_text)],
            states={
                WAIT_TEXT: [
                    MessageHandler(TEXT_FILTER, self.text_service.ask_pdf_font)
                ],
                WAIT_FONT: [MessageHandler(TEXT_FILTER, self.text_service.check_text)],
            },
            fallbacks=[
                CommandHandler("cancel", cancel),
            ],
            allow_reentry=True,
            run_async=True,
        )
