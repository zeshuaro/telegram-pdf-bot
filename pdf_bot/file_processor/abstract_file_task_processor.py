from abc import ABC, abstractmethod
from typing import Type

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import CallbackContext

from pdf_bot.consts import CANCEL
from pdf_bot.language import LanguageService

from .abstract_file_processor import AbstractFileProcessor


class AbstractFileTaskProcessor(ABC):
    WAIT_FILE_TASK = "wait_file_task"
    _KEYBOARD_SIZE = 3

    def __init__(self, language_service: LanguageService) -> None:
        self.language_service = language_service

    @property
    @abstractmethod
    def processor_type(self) -> Type[AbstractFileProcessor]:
        pass

    async def ask_task(self, update: Update, context: CallbackContext) -> str:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.effective_message  # type: ignore
        file = message.document or message.photo[-1]
        tasks = self.processor_type.get_task_data_list()

        keyboard = [
            [
                InlineKeyboardButton(
                    _(task.label),
                    callback_data=task.get_file_data(file),
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
