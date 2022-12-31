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

from .batch_image_service import BatchImageService


class BatchImageHandler(AbstractTelegramHandler):
    _IMAGE_COMMAND = "image"

    def __init__(
        self, batch_image_service: BatchImageService, telegram_service: TelegramService
    ) -> None:
        self.batch_image_service = batch_image_service
        self.telegram_service = telegram_service

    @property
    def handlers(self) -> list[BaseHandler]:
        return [
            ConversationHandler(
                entry_points=[
                    CommandHandler(self._IMAGE_COMMAND, self.batch_image_service.ask_first_image)
                ],
                states={
                    BatchImageService.WAIT_IMAGE: [
                        MessageHandler(
                            filters.Document.IMAGE | filters.PHOTO,
                            self.batch_image_service.check_image,
                        ),
                        MessageHandler(TEXT_FILTER, self.batch_image_service.check_text),
                    ]
                },
                fallbacks=[CommandHandler("cancel", self.telegram_service.cancel_conversation)],
                allow_reentry=True,
            )
        ]
