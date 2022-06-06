from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, PDF_INFO
from pdf_bot.encrypt import encrypt_constants
from pdf_bot.file_task import FileTaskService
from pdf_bot.files.utils import get_back_markup
from pdf_bot.language import set_lang
from pdf_bot.pdf import PdfService
from pdf_bot.telegram import TelegramService, TelegramServiceError
from pdf_bot.utils import send_result_file


class EncryptService:
    def __init__(
        self,
        file_task_service: FileTaskService,
        pdf_service: PdfService,
        telegram_service: TelegramService,
    ) -> None:
        self.file_task_service = file_task_service
        self.pdf_service = pdf_service
        self.telegram_service = telegram_service

    @staticmethod
    def ask_password(update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        update.effective_message.reply_text(
            _("Send me the password to encrypt your PDF file"),
            reply_markup=get_back_markup(update, context),
        )
        return encrypt_constants.WAIT_ENCRYPT_PASSWORD

    def encrypt_pdf(self, update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        message = update.effective_message

        if message.text == _(BACK):
            return self.file_task_service.ask_pdf_task(update, context)

        try:
            file_id, _file_name = self.telegram_service.get_user_data(context, PDF_INFO)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return ConversationHandler.END

        with self.pdf_service.encrypt_pdf(file_id, message.text) as out_path:
            send_result_file(update, context, out_path, TaskType.encrypt_pdf)

        return ConversationHandler.END
