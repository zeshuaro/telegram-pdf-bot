from gettext import gettext as _

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import CallbackContext

from pdf_bot.consts import CANCEL
from pdf_bot.image_processor.models import BeautifyImageData, ImageToPdfData
from pdf_bot.language import LanguageService
from pdf_bot.models import TaskData


class ImageProcessor:
    WAIT_IMAGE_TASK = "wait_image_task"

    _KEYBOARD_SIZE = 3
    _TASKS = [
        TaskData(_("Beautify"), "beautify_image", BeautifyImageData),
        TaskData(_("To PDF"), "image_to_pdf", ImageToPdfData),
    ]

    def __init__(self, language_service: LanguageService) -> None:
        self.language_service = language_service

    async def ask_image_task(self, update: Update, context: CallbackContext) -> str:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.effective_message  # type: ignore
        file = message.document or message.photo[-1]

        keyboard = [
            [
                InlineKeyboardButton(
                    _(task.label),
                    callback_data=task.get_file_data(file),
                )
                for task in self._TASKS[i : i + self._KEYBOARD_SIZE]
            ]
            for i in range(0, len(self._TASKS), self._KEYBOARD_SIZE)
        ]
        keyboard.append([InlineKeyboardButton(_(CANCEL), callback_data="cancel")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.effective_message.reply_text(  # type: ignore
            _("Select the task that you'll like to perform"), reply_markup=reply_markup
        )

        return self.WAIT_IMAGE_TASK
