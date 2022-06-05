from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import CallbackContext

from pdf_bot.consts import CANCEL
from pdf_bot.file_task import file_task_constants
from pdf_bot.language import set_lang


class FileTaskService:
    @staticmethod
    def ask_pdf_task(update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        keywords = [_(x) for x in file_task_constants.PDF_TASKS]
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

        return file_task_constants.WAIT_PDF_TASK
