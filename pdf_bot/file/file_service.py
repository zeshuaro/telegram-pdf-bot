from telegram import ParseMode, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import PDF_INFO
from pdf_bot.language import set_lang
from pdf_bot.pdf import PdfService, PdfServiceError
from pdf_bot.telegram import TelegramService, TelegramServiceError
from pdf_bot.utils import send_result_file


class FileService:
    def __init__(
        self, pdf_service: PdfService, telegram_service: TelegramService
    ) -> None:
        self.pdf_service = pdf_service
        self.telegram_service = telegram_service

    def compress_pdf(self, update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        message = update.effective_message

        try:
            file_id, _file_name = self.telegram_service.get_user_data(context, PDF_INFO)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return ConversationHandler.END

        with self.pdf_service.compress_pdf(file_id) as compress_result:
            message.reply_text(
                _(
                    "File size reduced by {percent}, from {old_size} to {new_size}"
                ).format(
                    percent="<b>{:.0%}</b>".format(compress_result.reduced_percentage),
                    old_size=f"<b>{compress_result.readable_old_size}</b>",
                    new_size=f"<b>{compress_result.readable_new_size}</b>",
                ),
                parse_mode=ParseMode.HTML,
            )
            send_result_file(
                update, context, compress_result.out_path, TaskType.compress_pdf
            )
        return ConversationHandler.END

    def extract_text_from_pdf(self, update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        message = update.effective_message

        try:
            file_id, _file_name = self.telegram_service.get_user_data(context, PDF_INFO)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return ConversationHandler.END

        with self.pdf_service.extract_text_from_pdf(file_id) as out_path:
            send_result_file(update, context, out_path, TaskType.get_pdf_text)
        return ConversationHandler.END

    def ocr_pdf(self, update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        message = update.effective_message
        message.reply_text(
            _("Adding an OCR text layer to your PDF file"),
            reply_markup=ReplyKeyboardRemove(),
        )

        try:
            file_id, _file_name = self.telegram_service.get_user_data(context, PDF_INFO)
            with self.pdf_service.ocr_pdf(file_id) as out_path:
                send_result_file(update, context, out_path, TaskType.ocr_pdf)
        except (TelegramServiceError, PdfServiceError) as e:
            message.reply_text(_(str(e)))
        return ConversationHandler.END
