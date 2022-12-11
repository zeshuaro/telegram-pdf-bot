from gettext import gettext as _

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import CallbackContext

from pdf_bot.consts import CANCEL
from pdf_bot.language import LanguageService


class FileTaskService:
    WAIT_PDF_TASK = "wait_pdf_task"
    WAIT_IMAGE_TASK = "wait_image_task"
    KEYBOARD_SIZE = 3

    PREVIEW = _("Preview")
    DECRYPT = _("Decrypt")
    ENCRYPT = _("Encrypt")
    EXTRACT_IMAGE = _("Extract Images")
    TO_IMAGES = _("To Images")
    ROTATE = _("Rotate")
    SCALE = _("Scale")
    SPLIT = _("Split")
    RENAME = _("Rename")
    CROP = _("Crop")
    EXTRACT_TEXT = _("Extract Text")
    OCR = "OCR"
    COMPRESS = _("Compress")
    BLACK_AND_WHITE = _("Black & White")

    BEAUTIFY = _("Beautify")
    TO_PDF = _("To PDF")

    PDF_TASKS = sorted(
        [
            DECRYPT,
            ENCRYPT,
            ROTATE,
            SCALE,
            SPLIT,
            PREVIEW,
            TO_IMAGES,
            EXTRACT_IMAGE,
            RENAME,
            CROP,
            EXTRACT_TEXT,
            OCR,
            COMPRESS,
            BLACK_AND_WHITE,
        ]
    )

    IMAGE_TASKS = sorted([BEAUTIFY, TO_PDF])

    def __init__(self, language_service: LanguageService) -> None:
        self.language_service = language_service

    def ask_pdf_task(self, update: Update, context: CallbackContext) -> str:
        self._reply_with_tasks(update, context, self.PDF_TASKS)
        return self.WAIT_PDF_TASK

    def ask_image_task(self, update: Update, context: CallbackContext) -> str:
        self._reply_with_tasks(update, context, self.IMAGE_TASKS)
        return self.WAIT_IMAGE_TASK

    def _reply_with_tasks(
        self, update: Update, context: CallbackContext, tasks: list[str]
    ) -> None:
        _ = self.language_service.set_app_language(update, context)
        translated_tasks = [_(x) for x in tasks]
        keyboard = [
            translated_tasks[i : i + self.KEYBOARD_SIZE]
            for i in range(0, len(translated_tasks), self.KEYBOARD_SIZE)
        ]
        keyboard.append([_(CANCEL)])

        reply_markup = ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True, one_time_keyboard=True
        )
        update.effective_message.reply_text(  # type: ignore
            _("Select the task that you'll like to perform"), reply_markup=reply_markup
        )
