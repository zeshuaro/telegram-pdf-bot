from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler

from pdf_bot.consts import TEXT_FILTER
from pdf_bot.image.constants import WAIT_IMAGE
from pdf_bot.image.image_service import ImageService
from pdf_bot.utils import cancel


class ImageHandlers:
    def __init__(self, image_service: ImageService) -> None:
        self.image_service = image_service

    def conversation_handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[CommandHandler("image", self.image_service.ask_first_image)],
            states={
                WAIT_IMAGE: [
                    MessageHandler(
                        Filters.document | Filters.photo, self.image_service.check_image
                    ),
                    MessageHandler(TEXT_FILTER, self.image_service.check_text),
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
            allow_reentry=True,
            run_async=True,
        )
