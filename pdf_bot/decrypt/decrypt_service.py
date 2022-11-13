from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, PDF_INFO
from pdf_bot.file_task import FileTaskService
from pdf_bot.language_new import LanguageService
from pdf_bot.pdf import PdfIncorrectPasswordError, PdfService, PdfServiceError
from pdf_bot.telegram import TelegramService, TelegramServiceError


class DecryptService:
    WAIT_DECRYPT_PASSWORD = "wait_decrypt_password"

    def __init__(
        self,
        file_task_service: FileTaskService,
        pdf_service: PdfService,
        telegram_service: TelegramService,
        language_service: LanguageService,
    ) -> None:
        self.file_task_service = file_task_service
        self.pdf_service = pdf_service
        self.telegram_service = telegram_service
        self.language_service = language_service

    def ask_password(self, update: Update, context: CallbackContext) -> str:
        _ = self.language_service.set_app_language(update, context)
        self.telegram_service.reply_with_back_markup(
            update, context, _("Send me the password to decrypt your PDF file")
        )

        return self.WAIT_DECRYPT_PASSWORD

    def decrypt_pdf(self, update: Update, context: CallbackContext) -> str | int:
        _ = self.language_service.set_app_language(update, context)
        message = update.effective_message

        if message.text == _(BACK):
            return self.file_task_service.ask_pdf_task(update, context)

        try:
            file_id, file_name = self.telegram_service.get_user_data(context, PDF_INFO)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return ConversationHandler.END

        try:
            with self.pdf_service.decrypt_pdf(file_id, message.text) as out_path:
                self.telegram_service.reply_with_file(
                    update, context, out_path, TaskType.decrypt_pdf
                )
        except PdfServiceError as e:
            message.reply_text(_(str(e)))
            if isinstance(e, PdfIncorrectPasswordError):
                context.user_data[PDF_INFO] = (file_id, file_name)
                return self.WAIT_DECRYPT_PASSWORD
        return ConversationHandler.END
