from gettext import gettext as _

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import CallbackContext

from pdf_bot.consts import CANCEL
from pdf_bot.language_new import LanguageService


class FileTaskService:
    WAIT_PDF_TASK = "wait_pdf_task"
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

    def __init__(self, language_service: LanguageService) -> None:
        self.language_service = language_service

    def ask_pdf_task(self, update: Update, context: CallbackContext) -> str:
        _ = self.language_service.set_app_language(update, context)
        keywords = [_(x) for x in self.PDF_TASKS]
        keyboard = [
            keywords[i : i + self.KEYBOARD_SIZE]
            for i in range(0, len(keywords), self.KEYBOARD_SIZE)
        ]
        keyboard.append([_(CANCEL)])

        reply_markup = ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True, one_time_keyboard=True
        )
        update.effective_message.reply_text(
            _("Select the task that you'll like to perform"), reply_markup=reply_markup
        )

        return self.WAIT_PDF_TASK
