from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes

from pdf_bot.consts import CANCEL, FILE_DATA
from pdf_bot.language import LanguageService
from pdf_bot.models import FileData, TaskData


class FileTaskMixin:
    WAIT_FILE_TASK = "wait_file_task"
    _KEYBOARD_SIZE = 3

    async def ask_task_helper(
        self,
        language_service: LanguageService,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        tasks: list[TaskData],
    ) -> str:
        _ = language_service.set_app_language(update, context)
        message: Message = update.effective_message  # type: ignore
        file_data: FileData | None = None

        # Try to retrieve the file data cached in user data first
        if context.user_data is not None:
            file_data = context.user_data.get(FILE_DATA)

        # If we can't retrieve the file data, then we get the document/photo attached to
        # the message
        if file_data is None:
            file = message.document or message.photo[-1]

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
        await message.reply_text(
            _("Select the task that you'll like to perform"), reply_markup=reply_markup
        )

        return self.WAIT_FILE_TASK
