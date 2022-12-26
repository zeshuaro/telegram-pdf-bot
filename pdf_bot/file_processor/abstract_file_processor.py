import os
import shutil
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Coroutine, Type

from telegram import CallbackQuery, Message, Update
from telegram.ext import ContextTypes, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, FILE_DATA
from pdf_bot.file_task import FileTaskService
from pdf_bot.language import LanguageService
from pdf_bot.models import FileData
from pdf_bot.telegram_internal import TelegramService, TelegramServiceError

ErrorHandlerType = Callable[
    [Update, ContextTypes.DEFAULT_TYPE, Exception, str, str | None],
    Coroutine[Any, Any, str | int],
]


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

    @asynccontextmanager
    @abstractmethod
    async def process_file_task(
        self, file_id: str, message_text: str
    ) -> AsyncGenerator[str, None]:
        yield ""

    @property
    def generic_error_types(self) -> set[Type[Exception]]:
        return set()

    @property
    def custom_error_handlers(
        self,
    ) -> dict[Type[Exception], ErrorHandlerType]:
        return {}

    async def process_file(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str | int:
        _ = self.language_service.set_app_language(update, context)
        query: CallbackQuery | None = update.callback_query
        message: Message = update.effective_message  # type: ignore

        if self.should_process_back_option and message.text == _(BACK):
            return await self.file_task_service.ask_pdf_task(update, context)

        if query is not None:
            data = query.data
            if not isinstance(data, FileData):
                raise ValueError(f"Unknown query data type: {type(query.data)}")

            await query.answer()
            await query.edit_message_text(_("Processing your file"))
            context.drop_callback_data(query)
            file_id, file_name = data.id, data.name
        else:
            try:
                file_id, file_name = self.telegram_service.get_user_data(
                    context, FILE_DATA
                )
            except TelegramServiceError as e:
                await message.reply_text(_(str(e)))
                return ConversationHandler.END

        try:
            async with self.process_file_task(file_id, message.text) as out_path:
                final_path = out_path
                if os.path.isdir(out_path):
                    shutil.make_archive(out_path, "zip", out_path)
                    final_path = f"{out_path}.zip"

                await self.telegram_service.send_file(
                    update, context, final_path, self.task_type
                )
        except Exception as e:  # pylint: disable=broad-except
            handlers = self._get_error_handlers()
            error_handler: ErrorHandlerType | None = None
            for error_type, handler in handlers.items():
                if isinstance(e, error_type):
                    error_handler = handler

            if error_handler is not None:
                return await error_handler(update, context, e, file_id, file_name)
        return ConversationHandler.END

    def _get_error_handlers(
        self,
    ) -> dict[Type[Exception], ErrorHandlerType]:
        handlers: dict[Type[Exception], ErrorHandlerType] = {
            x: self._handle_generic_error for x in self.generic_error_types
        }
        handlers.update(self.custom_error_handlers)
        return handlers

    async def _handle_generic_error(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        exception: Exception,
        _file_id: str,
        _file_name: str | None,
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        await update.effective_message.reply_text(_(str(exception)))  # type: ignore
        return ConversationHandler.END
