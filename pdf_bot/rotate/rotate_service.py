from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, PDF_INFO
from pdf_bot.file_task import FileTaskService
from pdf_bot.language import set_lang
from pdf_bot.pdf import PdfService
from pdf_bot.rotate import rotate_constants
from pdf_bot.telegram_internal import TelegramService, TelegramServiceError
from pdf_bot.utils import send_result_file


class RotateService:
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
    def ask_degree(update: Update, context: CallbackContext):
        _ = set_lang(update, context)

        keyboard = [
            [rotate_constants.ROTATE_90, rotate_constants.ROTATE_180],
            [rotate_constants.ROTATE_270, _(BACK)],
        ]
        reply_markup = ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True, one_time_keyboard=True
        )
        update.effective_message.reply_text(
            _(
                "Select the degrees that you'll like to "
                "rotate your PDF file in clockwise"
            ),
            reply_markup=reply_markup,
        )

        return rotate_constants.WAIT_ROTATE_DEGREE

    def rotate_pdf(self, update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        message = update.effective_message
        text = message.text

        if text == _(BACK):
            return self.file_task_service.ask_pdf_task(update, context)
        if text not in {
            rotate_constants.ROTATE_90,
            rotate_constants.ROTATE_180,
            rotate_constants.ROTATE_270,
        }:
            return None

        try:
            file_id, _file_name = self.telegram_service.get_user_data(context, PDF_INFO)
            with self.pdf_service.rotate_pdf(file_id, int(text)) as out_path:
                send_result_file(update, context, out_path, TaskType.rotate_pdf)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
        return ConversationHandler.END
