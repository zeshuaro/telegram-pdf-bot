from telegram.ext import (
    BaseHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
)

from pdf_bot.consts import TEXT_FILTER
from pdf_bot.telegram_handler import AbstractTelegramHandler
from pdf_bot.telegram_internal.telegram_service import TelegramService

from .feedback_service import FeedbackService


class FeedbackHandler(AbstractTelegramHandler):
    _FEEDBACK_COMMAND = "feedback"

    def __init__(
        self,
        feedback_service: FeedbackService,
        telegram_service: TelegramService,
    ) -> None:
        self.feedback_service = feedback_service
        self.telegram_service = telegram_service

    @property
    def handlers(self) -> list[BaseHandler]:
        return [
            ConversationHandler(
                entry_points=[
                    CommandHandler(
                        self._FEEDBACK_COMMAND, self.feedback_service.ask_feedback
                    )
                ],
                states={
                    FeedbackService.WAIT_FEEDBACK: [
                        MessageHandler(TEXT_FILTER, self.feedback_service.check_text)
                    ]
                },
                fallbacks=[
                    CommandHandler("cancel", self.telegram_service.cancel_conversation)
                ],
            )
        ]
