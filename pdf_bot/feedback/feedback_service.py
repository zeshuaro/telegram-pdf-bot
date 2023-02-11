from typing import cast

from langdetect import detect
from telegram import Message, Update, User
from telegram.ext import ContextTypes, ConversationHandler

from pdf_bot.consts import CANCEL
from pdf_bot.language import LanguageService
from pdf_bot.telegram_internal.telegram_service import TelegramService

from .feedback_repository import FeedbackRepository


class FeedbackService:
    WAIT_FEEDBACK = 0
    _VALID_LANGUAGE_CODE = "en"

    def __init__(
        self,
        feedback_repository: FeedbackRepository,
        language_service: LanguageService,
        telegram_service: TelegramService,
    ) -> None:
        self.feedback_repository = feedback_repository
        self.language_service = language_service
        self.telegram_service = telegram_service

    async def ask_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        _ = self.language_service.set_app_language(update, context)
        await self.telegram_service.reply_with_cancel_markup(
            update, context, _("Send me your feedback in English")
        )

        return self.WAIT_FEEDBACK

    async def check_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        _ = self.language_service.set_app_language(update, context)
        msg = cast(Message, update.effective_message)

        if msg.text == _(CANCEL):
            return await self.telegram_service.cancel_conversation(update, context)

        return await self._save_feedback(update, context)

    async def _save_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        _ = self.language_service.set_app_language(update, context)
        msg = cast(Message, update.effective_message)
        msg_user = cast(User, msg.from_user)
        msg_username = cast(str, msg_user.username)
        msg_text = cast(str, msg.text)

        feedback_lang = detect(msg.text)
        if feedback_lang.lower() != self._VALID_LANGUAGE_CODE:
            await msg.reply_text(_("The feedback is not in English, try again"))
            return self.WAIT_FEEDBACK

        self.feedback_repository.save_feedback(msg.chat.id, msg_username, msg_text)
        await msg.reply_text(_("Thank you for your feedback, I've forwarded it to my developer"))

        return ConversationHandler.END
