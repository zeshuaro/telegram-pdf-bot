from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler

from pdf_bot.compare.compare_service import CompareService
from pdf_bot.consts import TEXT_FILTER
from pdf_bot.telegram_internal import TelegramService


class CompareHandlers:
    def __init__(
        self, compare_service: CompareService, telegram_service: TelegramService
    ) -> None:
        self.compare_service = compare_service
        self.telegram_service = telegram_service

    def conversation_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[
                CommandHandler("compare", self.compare_service.ask_first_pdf)
            ],
            states={
                CompareService.WAIT_FIRST_PDF: [
                    MessageHandler(
                        Filters.document, self.compare_service.check_first_pdf
                    )
                ],
                CompareService.WAIT_SECOND_PDF: [
                    MessageHandler(Filters.document, self.compare_service.compare_pdfs)
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.telegram_service.cancel_conversation),
                MessageHandler(TEXT_FILTER, self.compare_service.check_text),
            ],
            allow_reentry=True,
            run_async=True,
        )
