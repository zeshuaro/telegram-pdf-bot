from gettext import gettext as _

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from pdf_bot.consts import CANCEL
from pdf_bot.language import LanguageService


class FileTaskService:
    WAIT_FILE_TASK = "wait_file_task"
    WAIT_IMAGE_TASK = "wait_image_task"
    KEYBOARD_SIZE = 3

    PREVIEW = _("Preview")
    DECRYPT = _("Decrypt")
    ENCRYPT = _("Encrypt")
    TO_IMAGES = _("To Images")
    ROTATE = _("Rotate")
    SCALE = _("Scale")
    SPLIT = _("Split")
    RENAME = _("Rename")
    CROP = _("Crop")
    COMPRESS = _("Compress")

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
            RENAME,
            CROP,
            COMPRESS,
        ]
    )

    IMAGE_TASKS = sorted([BEAUTIFY, TO_PDF])

    def __init__(self, language_service: LanguageService) -> None:
        self.language_service = language_service

    async def ask_pdf_task(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        await self._reply_with_tasks(update, context, self.PDF_TASKS)
        return self.WAIT_FILE_TASK

    async def ask_image_task(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        await self._reply_with_tasks(update, context, self.IMAGE_TASKS)
        return self.WAIT_IMAGE_TASK

    async def _reply_with_tasks(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, tasks: list[str]
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
        await update.effective_message.reply_text(  # type: ignore
            _(
                "Select the task that you'll like to perform from below or select from"
                " the buttons"
            ),
            reply_markup=reply_markup,
        )
