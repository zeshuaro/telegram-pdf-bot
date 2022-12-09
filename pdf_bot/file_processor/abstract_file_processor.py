import os
import shutil
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Callable, Generator, Type

from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, FILE_DATA
from pdf_bot.file_task import FileTaskService
from pdf_bot.language_new import LanguageService
from pdf_bot.telegram_internal import TelegramService, TelegramServiceError

ErrorHandlerType = Callable[[Update, CallbackContext, Exception, str, str], str]


class AbstractFileProcessor(ABC):
    def __init__(
        self,
        file_task_service: FileTaskService,
        telegram_service: TelegramService,
        language_service: LanguageService,
    ) -> None:
        self.file_task_service = file_task_service
        self.telegram_service = telegram_service
        self.language_service = language_service

    @property
    @abstractmethod
    def task_type(self) -> TaskType:
        pass

    @property
    @abstractmethod
    def should_process_back_option(self) -> bool:
        pass

    @abstractmethod
    @contextmanager
    def process_file_task(
        self, file_id: str, message_text: str
    ) -> Generator[str, None, None]:
        pass

    @property
    def generic_error_types(self) -> set[Type[Exception]]:
        return set()

    @property
    def custom_error_handlers(
        self,
    ) -> dict[Type[Exception], ErrorHandlerType]:
        return {}

    def process_file(self, update: Update, context: CallbackContext) -> str | int:
        _ = self.language_service.set_app_language(update, context)
        message = update.effective_message

        if self.should_process_back_option and message.text == _(BACK):
            return self.file_task_service.ask_pdf_task(update, context)

        try:
            file_id, file_name = self.telegram_service.get_user_data(context, FILE_DATA)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return ConversationHandler.END

        try:
            with self.process_file_task(file_id, message.text) as out_path:
                final_path = out_path
                if os.path.isdir(out_path):
                    shutil.make_archive(out_path, "zip", out_path)
                    final_path = f"{out_path}.zip"

                self.telegram_service.reply_with_file(
                    update, context, final_path, self.task_type
                )
        except Exception as e:  # pylint: disable=broad-except
            handlers = self._get_error_handlers()
            error_handler: ErrorHandlerType | None = None
            for error_type, handler in handlers.items():
                if isinstance(e, error_type):
                    error_handler = handler

            if error_handler is not None:
                return error_handler(update, context, e, file_id, file_name)
        return ConversationHandler.END

    def _get_error_handlers(
        self,
    ) -> dict[Type[Exception], ErrorHandlerType]:
        handlers = {x: self._handle_generic_error for x in self.generic_error_types}
        handlers.update(self.custom_error_handlers)
        return handlers

    def _handle_generic_error(
        self,
        update: Update,
        context: CallbackContext,
        exception: Exception,
        _file_id: str,
        _file_name: str,
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        update.effective_message.reply_text(_(str(exception)))
        return ConversationHandler.END
