from abc import ABC, abstractmethod

from telegram import Update
from telegram.ext import CallbackContext

from pdf_bot.language import LanguageService

from .abstract_file_processor import AbstractFileProcessor
from .file_task_mixin import FileTaskMixin


class AbstractFileTaskProcessor(FileTaskMixin, ABC):
    def __init__(self, language_service: LanguageService) -> None:
        self.language_service = language_service

    @property
    @abstractmethod
    def processor_type(self) -> type[AbstractFileProcessor]:
        pass

    async def ask_task(self, update: Update, context: CallbackContext) -> str:
        return await self.ask_task_helper(
            self.language_service,
            update,
            context,
            self.processor_type.get_task_data_list(),
        )
