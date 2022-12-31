from telegram.ext import (
    BaseHandler,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from pdf_bot.file_processor import AbstractFileProcessor
from pdf_bot.telegram_handler import AbstractTelegramHandler
from pdf_bot.telegram_internal import TelegramService

from .file_service import FileService


class FileHandler(AbstractTelegramHandler):
    def __init__(self, file_service: FileService, telegram_service: TelegramService) -> None:
        self.file_service = file_service
        self.telegram_service = telegram_service

    @property
    def handlers(self) -> list[BaseHandler]:
        return [
            ConversationHandler(
                entry_points=[
                    MessageHandler(filters.Document.PDF, self.file_service.check_pdf),
                    MessageHandler(
                        filters.PHOTO | filters.Document.IMAGE,
                        self.file_service.check_image,
                    ),
                ],
                states={AbstractFileProcessor.WAIT_FILE_TASK: AbstractFileProcessor.get_handlers()},
                fallbacks=[
                    CallbackQueryHandler(
                        self.telegram_service.cancel_conversation,
                        pattern=r"^cancel$",
                    ),
                    CommandHandler("cancel", self.telegram_service.cancel_conversation),
                ],
                allow_reentry=True,
            )
        ]
