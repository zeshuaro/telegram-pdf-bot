from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler

from pdf_bot.consts import TEXT_FILTER
from pdf_bot.merge.constants import WAIT_MERGE_PDF
from pdf_bot.merge.merge_service import MergeService
from pdf_bot.utils import cancel


class MergeHandlers:
    def __init__(self, merge_service: MergeService) -> None:
        self.merge_service = merge_service

    def conversation_handler(self):
        return ConversationHandler(
            entry_points=[CommandHandler("merge", self.merge_service.ask_first_pdf)],
            states={
                WAIT_MERGE_PDF: [
                    MessageHandler(
                        Filters.document, self.merge_service.check_pdf_for_merge
                    ),
                    MessageHandler(TEXT_FILTER, self.merge_service.check_text),
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
            allow_reentry=True,
            run_async=True,
        )
