from typing import cast

from telegram import Message, Update
from telegram.ext import ContextTypes

from pdf_bot.language import LanguageService


class ErrorService:
    def __init__(self, language_service: LanguageService) -> None:
        self.language_service = language_service

    async def process_unknown_callback_query(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        _ = self.language_service.set_app_language(update, context)
        text = _("The button has expired, start over with your file or command")

        query = update.callback_query
        await query.answer(text)

        message = cast(Message, update.effective_message)
        await message.reply_text(text)
