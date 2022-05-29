from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, CANCEL, PDF_INVALID_FORMAT, PDF_OK
from pdf_bot.language import set_lang
from pdf_bot.pdf import PdfServiceError
from pdf_bot.pdf.pdf_service import PdfService
from pdf_bot.utils import cancel, check_pdf, check_user_data, send_result_file
from pdf_bot.watermark.constants import (
    WAIT_SOURCE_PDF,
    WAIT_WATERMARK_PDF,
    WATERMARK_KEY,
)


class WatermarkService:
    def __init__(self, pdf_service: PdfService) -> None:
        self.pdf_service = pdf_service

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

    @staticmethod
    def check_source_pdf(update: Update, context: CallbackContext):
        result = check_pdf(update, context)
        if result == PDF_INVALID_FORMAT:
            return WAIT_SOURCE_PDF
        if result != PDF_OK:
            return ConversationHandler.END

        _ = set_lang(update, context)
        context.user_data[WATERMARK_KEY] = update.effective_message.document.file_id

        reply_markup = ReplyKeyboardMarkup(
            [[_(BACK), _(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
        )
        update.effective_message.reply_text(
            _("Send me the watermark PDF file"), reply_markup=reply_markup
        )

        return WAIT_WATERMARK_PDF

    def check_watermark_pdf(self, update: Update, context: CallbackContext):
        if not check_user_data(update, context, WATERMARK_KEY):
            return ConversationHandler.END

        result = check_pdf(update, context)
        if result == PDF_INVALID_FORMAT:
            return WAIT_WATERMARK_PDF
        if result != PDF_OK:
            return ConversationHandler.END

        return self.add_watermark(update, context)

    def add_watermark(self, update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        update.effective_message.reply_text(
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
            update.effective_message.reply_text(_(e))

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
