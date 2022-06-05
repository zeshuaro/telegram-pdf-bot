from telegram import ParseMode, ReplyKeyboardMarkup, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import CANCEL, PDF_INFO
from pdf_bot.file import file_constants
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

    @staticmethod
    def ask_pdf_task(update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        keywords = [_(x) for x in file_constants.PDF_TASKS]
        keyboard_size = 3
        keyboard = [
            keywords[i : i + keyboard_size]
            for i in range(0, len(keywords), keyboard_size)
        ]
        keyboard.append([_(CANCEL)])

        reply_markup = ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True, one_time_keyboard=True
        )
        update.effective_message.reply_text(
            _("Select the task that you'll like to perform"), reply_markup=reply_markup
        )

        return file_constants.WAIT_PDF_TASK

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
