from abc import ABC, abstractmethod
from typing import Type

from telegram import Update
from telegram.ext import CallbackContext

from pdf_bot.language import LanguageService

from .abstract_file_processor import AbstractFileProcessor
from .file_task_mixin import FileTaskMixin


class AbstractFileTaskProcessor(FileTaskMixin, ABC):
    WAIT_FILE_TASK = "wait_file_task"
    _KEYBOARD_SIZE = 3

    def __init__(self, language_service: LanguageService) -> None:
        self.language_service = language_service

    @property
    @abstractmethod
    def processor_type(self) -> Type[AbstractFileProcessor]:
        pass

    async def ask_task(self, update: Update, context: CallbackContext) -> str:
        return await self.ask_task_helper(
            self.language_service,
            update,
            context,
            self.processor_type.get_task_data_list(),
        )
