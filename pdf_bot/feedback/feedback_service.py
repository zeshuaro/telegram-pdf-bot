from langdetect import detect
from telegram import Message, Update
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
        if update.effective_message.text == _(CANCEL):  # type: ignore
            return await self.telegram_service.cancel_conversation(update, context)

        return await self._save_feedback(update, context)

    async def _save_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.effective_message  # type: ignore

        feedback_lang = detect(message.text)
        if feedback_lang.lower() != self._VALID_LANGUAGE_CODE:
            await message.reply_text(_("The feedback is not in English, try again"))
            return self.WAIT_FEEDBACK

        self.feedback_repository.save_feedback(
            message.chat.id, message.from_user.username, message.text
        )
        await message.reply_text(
            _("Thank you for your feedback, I've forwarded it to my developer")
        )

        return ConversationHandler.END
