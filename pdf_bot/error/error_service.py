from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from pdf_bot.language import LanguageService


class ErrorService:
    def __init__(self, language_service: LanguageService) -> None:
        self.language_service = language_service

    async def process_unknown_callback_query(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        await query.answer()

        _ = self.language_service.set_app_language(update, context)
        err_text = _("The button has expired, start over with your file or command")

        try:
            await query.edit_message_text(err_text)
        except BadRequest:
            try:
                await query.delete_message()
            except BadRequest:
                pass
            await update.effective_message.reply_text(err_text)  # type: ignore
