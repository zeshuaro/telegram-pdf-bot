from typing import cast

from telegram import Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, CANCEL
from pdf_bot.language import LanguageService
from pdf_bot.pdf import PdfServiceError
from pdf_bot.pdf.pdf_service import PdfService
from pdf_bot.telegram_internal import (
    TelegramGetUserDataError,
    TelegramService,
    TelegramServiceError,
)


class WatermarkService:
    WAIT_SOURCE_PDF = 0
    WAIT_WATERMARK_PDF = 1
    WATERMARK_KEY = "watermark"

    def __init__(
        self,
        pdf_service: PdfService,
        telegram_service: TelegramService,
        language_service: LanguageService,
    ) -> None:
        self.pdf_service = pdf_service
        self.telegram_service = telegram_service
        self.language_service = language_service

    async def ask_source_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        _ = self.language_service.set_app_language(update, context)
        await self.telegram_service.reply_with_cancel_markup(
            update,
            context,
            _("Send me the PDF file that you'll like to add a watermark"),
        )
        return self.WAIT_SOURCE_PDF

    async def check_source_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        _ = self.language_service.set_app_language(update, context)
        msg = cast("Message", update.effective_message)

        try:
            doc = self.telegram_service.check_pdf_document(msg)
        except TelegramServiceError as e:
            await msg.reply_text(_(str(e)))
            return self.WAIT_SOURCE_PDF

        self.telegram_service.update_user_data(context, self.WATERMARK_KEY, doc.file_id)
        reply_markup = ReplyKeyboardMarkup(
            [[_(BACK), _(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
        )
        await msg.reply_text(_("Send me the watermark PDF file"), reply_markup=reply_markup)

        return self.WAIT_WATERMARK_PDF

    async def add_watermark_to_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        _ = self.language_service.set_app_language(update, context)
        msg = cast("Message", update.effective_message)

        try:
            doc = self.telegram_service.check_pdf_document(msg)
            src_file_id = self.telegram_service.get_user_data(context, self.WATERMARK_KEY)
        except TelegramServiceError as e:
            await msg.reply_text(_(str(e)))
            if isinstance(e, TelegramGetUserDataError):
                return ConversationHandler.END
            return self.WAIT_WATERMARK_PDF

        await msg.reply_text(
            _("Adding the watermark onto your PDF file"),
            reply_markup=ReplyKeyboardRemove(),
        )

        try:
            async with self.pdf_service.add_watermark_to_pdf(src_file_id, doc.file_id) as out_path:
                await self.telegram_service.send_file(
                    update, context, out_path, TaskType.watermark_pdf
                )
        except PdfServiceError as e:
            await msg.reply_text(_(str(e)))

        return ConversationHandler.END

    async def check_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
        _ = self.language_service.set_app_language(update, context)
        msg = cast("Message", update.effective_message)
        text = msg.text

        if text == _(BACK):
            return await self.ask_source_pdf(update, context)
        if text == _(CANCEL):
            return await self.telegram_service.cancel_conversation(update, context)

        return None
