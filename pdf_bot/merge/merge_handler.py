from telegram.ext import (
    BaseHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from pdf_bot.consts import TEXT_FILTER
from pdf_bot.merge.merge_service import MergeService
from pdf_bot.telegram_handler import AbstractTelegramHandler
from pdf_bot.telegram_internal import TelegramService

from .merge_service import MergeService


class MergeHandler(AbstractTelegramHandler):
    _MERGE_COMMAND = "merge"

    def __init__(
        self, merge_service: MergeService, telegram_service: TelegramService
    ) -> None:
        self.merge_service = merge_service
        self.telegram_service = telegram_service

    @property
    def handlers(self) -> list[BaseHandler]:
        return [
            ConversationHandler(
                entry_points=[
                    CommandHandler(
                        self._MERGE_COMMAND, self.merge_service.ask_first_pdf
                    )
                ],
                states={
                    MergeService.WAIT_MERGE_PDF: [
                        MessageHandler(
                            filters.Document.PDF, self.merge_service.check_pdf
                        ),
                        MessageHandler(TEXT_FILTER, self.merge_service.check_text),
                    ],
                },
                fallbacks=[
                    CommandHandler("cancel", self.telegram_service.cancel_conversation)
                ],
                allow_reentry=True,
            )
        ]
