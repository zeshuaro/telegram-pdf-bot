from telegram.ext import (
    BaseHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from pdf_bot.consts import TEXT_FILTER
from pdf_bot.telegram_handler import AbstractTelegramHandler
from pdf_bot.telegram_internal import TelegramService

from .compare_service import CompareService


class CompareHandler(AbstractTelegramHandler):
    _COMPARE_COMMAND = "compare"

    def __init__(
        self, compare_service: CompareService, telegram_service: TelegramService
    ) -> None:
        self.compare_service = compare_service
        self.telegram_service = telegram_service

    @property
    def handlers(self) -> list[BaseHandler]:
        return [
            ConversationHandler(
                entry_points=[
                    CommandHandler(
                        self._COMPARE_COMMAND, self.compare_service.ask_first_pdf
                    )
                ],
                states={
                    CompareService.WAIT_FIRST_PDF: [
                        MessageHandler(
                            filters.Document.PDF, self.compare_service.check_first_pdf
                        )
                    ],
                    CompareService.WAIT_SECOND_PDF: [
                        MessageHandler(
                            filters.Document.PDF, self.compare_service.compare_pdfs
                        )
                    ],
                },
                fallbacks=[
                    CommandHandler("cancel", self.telegram_service.cancel_conversation),
                    MessageHandler(TEXT_FILTER, self.compare_service.check_text),
                ],
                allow_reentry=True,
            )
        ]
