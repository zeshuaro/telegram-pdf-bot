from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler

from pdf_bot.consts import TEXT_FILTER
from pdf_bot.merge.merge_service import MergeService
from pdf_bot.telegram_internal import TelegramService


class MergeHandlers:
    def __init__(
        self, merge_service: MergeService, telegram_service: TelegramService
    ) -> None:
        self.merge_service = merge_service
        self.telegram_service = telegram_service

    def conversation_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[CommandHandler("merge", self.merge_service.ask_first_pdf)],
            states={
                MergeService.WAIT_MERGE_PDF: [
                    MessageHandler(Filters.document, self.merge_service.check_pdf),
                    MessageHandler(TEXT_FILTER, self.merge_service.check_text),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.telegram_service.cancel_conversation)
            ],
            allow_reentry=True,
            run_async=True,
        )
