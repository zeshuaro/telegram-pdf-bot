from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler

from pdf_bot.consts import TEXT_FILTER
from pdf_bot.utils import cancel
from pdf_bot.watermark.constants import WAIT_SOURCE_PDF, WAIT_WATERMARK_PDF
from pdf_bot.watermark.watermark_service import WatermarkService


class WatermarkHandlers:
    def __init__(self, watermark_service: WatermarkService) -> None:
        self.watermark_service = watermark_service

    def conversation_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[
                CommandHandler("watermark", self.watermark_service.ask_source_pdf)
            ],
            states={
                WAIT_SOURCE_PDF: [
                    MessageHandler(
                        Filters.document, self.watermark_service.check_source_pdf
                    )
                ],
                WAIT_WATERMARK_PDF: [
                    MessageHandler(
                        Filters.document, self.watermark_service.add_watermark_to_pdf
                    )
                ],
            },
            fallbacks=[
                CommandHandler("cancel", cancel),
                MessageHandler(TEXT_FILTER, self.watermark_service.check_text),
            ],
            allow_reentry=True,
            run_async=True,
        )
