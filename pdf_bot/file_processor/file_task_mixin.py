from typing import cast

from telegram import (
    Document,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PhotoSize,
    Update,
)
from telegram.ext import ContextTypes, ConversationHandler

from pdf_bot.consts import CANCEL, FILE_DATA, GENERIC_ERROR
from pdf_bot.language import LanguageService
from pdf_bot.models import FileData, TaskData


class FileTaskMixin:
    WAIT_FILE_TASK = "wait_file_task"
    _KEYBOARD_SIZE = 2

    async def ask_task_helper(
        self,
        language_service: LanguageService,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        tasks: list[TaskData],
    ) -> str | int:
        _ = language_service.set_app_language(update, context)
        msg = cast(Message, update.effective_message)
        file_data: FileData | None = None

        # Try to retrieve the file data cached in user data first
        if context.user_data is not None:
            file_data = context.user_data.get(FILE_DATA)

        # If we can't retrieve the file data, then we get the document/photo attached to
        # the message
        msg_doc: Document | None = msg.document
        msg_photo: tuple[PhotoSize, ...] | None = msg.photo
        if file_data is None and msg_doc is None and msg_photo is None:
            await msg.reply_text(_(GENERIC_ERROR))
            return ConversationHandler.END

        file = msg_doc or msg_photo[-1]  # type: ignore[index]

        def get_callback_data(data_type: type[FileData]) -> FileData:
            if file_data is not None:
                return data_type(file_data.id, file_data.name)
            return data_type.from_telegram_object(file)

        keyboard = [
            [
                InlineKeyboardButton(
                    _(task.label),
                    callback_data=get_callback_data(task.data_type),
                )
                for task in tasks[i : i + self._KEYBOARD_SIZE]
                if task is not None
            ]
            for i in range(0, len(tasks), self._KEYBOARD_SIZE)
        ]
        keyboard.append([InlineKeyboardButton(_(CANCEL), callback_data="cancel")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await msg.reply_text(
            _("Select the task that you'll like to perform"), reply_markup=reply_markup
        )

        return self.WAIT_FILE_TASK
