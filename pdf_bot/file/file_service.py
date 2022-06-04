from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import PDF_INFO
from pdf_bot.language import set_lang
from pdf_bot.pdf import PdfService
from pdf_bot.telegram import TelegramService, TelegramServiceError
from pdf_bot.utils import send_result_file


class FileService:
    def __init__(
        self, pdf_service: PdfService, telegram_service: TelegramService
    ) -> None:
        self.pdf_service = pdf_service
        self.telegram_service = telegram_service

    def black_and_white_pdf(self, update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        message = update.effective_message

        try:
            file_id, _ = self.telegram_service.get_user_data(context, PDF_INFO)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return ConversationHandler.END

        with self.pdf_service.black_and_white_pdf(file_id) as out_path:
            send_result_file(update, context, out_path, TaskType.black_and_white_pdf)
        return ConversationHandler.END
