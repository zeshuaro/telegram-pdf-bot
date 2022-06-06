import re

from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, PDF_INFO
from pdf_bot.file_task import FileTaskService
from pdf_bot.files.utils import get_back_markup
from pdf_bot.language import set_lang
from pdf_bot.pdf import PdfService
from pdf_bot.rename import rename_constants
from pdf_bot.telegram import TelegramService, TelegramServiceError
from pdf_bot.utils import send_result_file


class RenameService:
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
    def ask_new_file_name(update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        update.effective_message.reply_text(
            _("Send me the file name that you'll like to rename your PDF file into"),
            reply_markup=get_back_markup(update, context),
        )
        return rename_constants.WAIT_NEW_FILE_NAME

    def rename_pdf(self, update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        message = update.effective_message

        if message.text == _(BACK):
            return self.file_task_service.ask_pdf_task(update, context)

        text = re.sub(r"\.pdf$", "", message.text)
        if set(text) & set(rename_constants.INVALID_CHARACTERS):
            message.reply_text(
                "{desc_1}\n{invalid_chars}\n{desc_2}".format(
                    desc_1=_(
                        "File names can't contain any of the following characters:"
                    ),
                    invalid_chars=rename_constants.INVALID_CHARACTERS,
                    desc_2=_("Please try again"),
                ),
            )
            return rename_constants.WAIT_NEW_FILE_NAME

        try:
            file_id, _file_name = self.telegram_service.get_user_data(context, PDF_INFO)
            with self.pdf_service.rename_pdf(file_id, f"{text}.pdf") as out_path:
                send_result_file(update, context, out_path, TaskType.rename_pdf)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
        return ConversationHandler.END
