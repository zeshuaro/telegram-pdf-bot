from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler

from pdf_bot.compare.compare_service import CompareService
from pdf_bot.compare.constants import WAIT_FIRST_PDF, WAIT_SECOND_PDF
from pdf_bot.consts import TEXT_FILTER
from pdf_bot.utils import cancel


class CompareHandlers:
    def __init__(self, compare_service: CompareService) -> None:
        self.compare_service = compare_service

    def conversation_handler(self):
        return ConversationHandler(
            entry_points=[
                CommandHandler("compare", self.compare_service.ask_first_pdf)
            ],
            states={
                WAIT_FIRST_PDF: [
                    MessageHandler(
                        Filters.document, self.compare_service.check_first_pdf
                    )
                ],
                WAIT_SECOND_PDF: [
                    MessageHandler(
                        Filters.document, self.compare_service.check_second_pdf
                    )
                ],
            },
            fallbacks=[
                CommandHandler("cancel", cancel),
                MessageHandler(TEXT_FILTER, self.compare_service.check_text),
            ],
            allow_reentry=True,
            run_async=True,
        )
