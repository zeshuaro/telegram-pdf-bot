from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, CANCEL
from pdf_bot.language import set_lang
from pdf_bot.pdf import PdfServiceError
from pdf_bot.pdf.pdf_service import PdfService
from pdf_bot.telegram import (
    TelegramService,
    TelegramServiceError,
    TelegramUserDataKeyError,
)
from pdf_bot.utils import cancel, send_result_file
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
            doc = self.telegram_service.check_pdf_document(message)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return WAIT_SOURCE_PDF

        context.user_data[WATERMARK_KEY] = doc.file_id
        reply_markup = ReplyKeyboardMarkup(
            [[_(BACK), _(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
        )
        message.reply_text(
            _("Send me the watermark PDF file"), reply_markup=reply_markup
        )

        return WAIT_WATERMARK_PDF

    def add_watermark_to_pdf(self, update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        message = update.effective_message

        try:
            src_file_id = self.telegram_service.get_user_data(context, WATERMARK_KEY)
            doc = self.telegram_service.check_pdf_document(message)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            if isinstance(e, TelegramUserDataKeyError):
                return ConversationHandler.END
            return WAIT_WATERMARK_PDF

        message.reply_text(
            _("Adding the watermark onto your PDF file"),
            reply_markup=ReplyKeyboardRemove(),
        )

        try:
            with self.pdf_service.add_watermark_to_pdf(
                src_file_id, doc.file_id
            ) as out_path:
                send_result_file(update, context, out_path, TaskType.watermark_pdf)
        except PdfServiceError as e:
            message.reply_text(_(str(e)))

        return ConversationHandler.END

    def check_text(self, update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        text = update.effective_message.text

        if text == _(BACK):
            return self.ask_source_pdf(update, context)
        if text == _(CANCEL):
            return cancel(update, context)

        return None
