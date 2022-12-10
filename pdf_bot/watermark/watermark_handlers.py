from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler

from pdf_bot.consts import TEXT_FILTER
from pdf_bot.telegram_internal import TelegramService
from pdf_bot.watermark.watermark_service import WatermarkService


class WatermarkHandlers:
    def __init__(
        self, watermark_service: WatermarkService, telegram_service: TelegramService
    ) -> None:
        self.watermark_service = watermark_service
        self.telegram_service = telegram_service

    def conversation_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[
                CommandHandler("watermark", self.watermark_service.ask_source_pdf)
            ],
            states={
                WatermarkService.WAIT_SOURCE_PDF: [
                    MessageHandler(
                        Filters.document, self.watermark_service.check_source_pdf
                    )
                ],
                WatermarkService.WAIT_WATERMARK_PDF: [
                    MessageHandler(
                        Filters.document, self.watermark_service.add_watermark_to_pdf
                    )
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.telegram_service.cancel_conversation),
                MessageHandler(TEXT_FILTER, self.watermark_service.check_text),
            ],
            allow_reentry=True,
            run_async=True,
        )
