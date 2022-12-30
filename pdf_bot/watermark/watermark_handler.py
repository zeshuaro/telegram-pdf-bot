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

from .watermark_service import WatermarkService


class WatermarkHandler(AbstractTelegramHandler):
    _WATERMARK_COMMAND = "watermark"

    def __init__(
        self, watermark_service: WatermarkService, telegram_service: TelegramService
    ) -> None:
        self.watermark_service = watermark_service
        self.telegram_service = telegram_service

    @property
    def handlers(self) -> list[BaseHandler]:
        return [
            ConversationHandler(
                entry_points=[
                    CommandHandler(
                        self._WATERMARK_COMMAND, self.watermark_service.ask_source_pdf
                    )
                ],
                states={
                    WatermarkService.WAIT_SOURCE_PDF: [
                        MessageHandler(
                            filters.Document.PDF,
                            self.watermark_service.check_source_pdf,
                        )
                    ],
                    WatermarkService.WAIT_WATERMARK_PDF: [
                        MessageHandler(
                            filters.Document.PDF,
                            self.watermark_service.add_watermark_to_pdf,
                        )
                    ],
                },
                fallbacks=[
                    CommandHandler("cancel", self.telegram_service.cancel_conversation),
                    MessageHandler(TEXT_FILTER, self.watermark_service.check_text),
                ],
                allow_reentry=True,
            )
        ]
