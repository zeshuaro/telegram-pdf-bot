from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, CANCEL
from pdf_bot.language import set_lang
from pdf_bot.pdf import PdfServiceError
from pdf_bot.pdf.pdf_service import PdfService
from pdf_bot.telegram import TelegramService, TelegramServiceError
from pdf_bot.utils import cancel, check_user_data, send_result_file
from pdf_bot.watermark.constants import (
    WAIT_SOURCE_PDF,
    WAIT_WATERMARK_PDF,
    WATERMARK_KEY,
)


class WatermarkService:
    def __init__(
        self, pdf_service: PdfService, telegram_service: TelegramService
    ) -> None:
        self.pdf_service = pdf_service
        self.telegram_service = telegram_service

    @staticmethod
    def ask_source_pdf(update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        reply_markup = ReplyKeyboardMarkup(
            [[_(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
        )
        update.effective_message.reply_text(
            _("Send me the PDF file that you'll like to add a watermark"),
            reply_markup=reply_markup,
        )

        return WAIT_SOURCE_PDF

    def check_source_pdf(self, update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        message = update.effective_message

        try:
            self.telegram_service.check_pdf_document(message.document)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return WAIT_SOURCE_PDF

        context.user_data[WATERMARK_KEY] = message.document.file_id
        reply_markup = ReplyKeyboardMarkup(
            [[_(BACK), _(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
        )
        message.reply_text(
            _("Send me the watermark PDF file"), reply_markup=reply_markup
        )

        return WAIT_WATERMARK_PDF

    def add_watermark_to_pdf(self, update: Update, context: CallbackContext):
        if not check_user_data(update, context, WATERMARK_KEY):
            return ConversationHandler.END

        _ = set_lang(update, context)
        message = update.effective_message

        try:
            self.telegram_service.check_pdf_document(message.document)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return WAIT_WATERMARK_PDF

        message.reply_text(
            _("Adding the watermark onto your PDF file"),
            reply_markup=ReplyKeyboardRemove(),
        )

        user_data = context.user_data
        src_file_id = user_data[WATERMARK_KEY]
        wmk_file_id = update.effective_message.document.file_id

        try:
            with self.pdf_service.add_watermark_to_pdf(
                src_file_id, wmk_file_id
            ) as out_path:
                send_result_file(update, context, out_path, TaskType.watermark_pdf)
        except PdfServiceError as e:
            update.effective_message.reply_text(_(str(e)))

        if user_data[WATERMARK_KEY] == src_file_id:
            del user_data[WATERMARK_KEY]

        return ConversationHandler.END

    def check_text(self, update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        text = update.effective_message.text

        if text == _(BACK):
            return self.ask_source_pdf(update, context)
        if text == _(CANCEL):
            return cancel(update, context)

        return None
