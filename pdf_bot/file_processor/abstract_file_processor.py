import os
import shutil
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Coroutine, Type

from telegram import CallbackQuery, Message, Update
from telegram.error import BadRequest
from telegram.ext import BaseHandler, ContextTypes, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.language import LanguageService
from pdf_bot.models import FileData, TaskData
from pdf_bot.telegram_internal import TelegramGetUserDataError, TelegramService

from .file_task_mixin import FileTaskMixin

ErrorHandlerType = Callable[
    [Update, ContextTypes.DEFAULT_TYPE, Exception, FileData],
    Coroutine[Any, Any, str | int],
]


class AbstractFileProcessor(FileTaskMixin, ABC):
    _FILE_PROCESSORS: dict[str, "AbstractFileProcessor"] = {}

    def __init__(
        self,
        telegram_service: TelegramService,
        language_service: LanguageService,
        bypass_init_check: bool = False,
    ) -> None:
        self.telegram_service = telegram_service
        self.language_service = language_service

        cls_name = self.__class__.__name__
        if not bypass_init_check and cls_name in self._FILE_PROCESSORS:
            raise ValueError(f"Class has already been initialised: {cls_name}")
        self._FILE_PROCESSORS[cls_name] = self

    @classmethod
    @abstractmethod
    def get_task_data_list(cls) -> list[TaskData]:
        pass

    @classmethod
    def get_handlers(cls) -> list[BaseHandler]:
        return [
            x.handler for x in cls._FILE_PROCESSORS.values() if x.handler is not None
        ]

    @property
    @abstractmethod
    def task_type(self) -> TaskType:
        pass

    @property
    def task_data(self) -> TaskData | None:
        return None

    @property
    def handler(self) -> BaseHandler | None:
        return None

    @asynccontextmanager
    @abstractmethod
    async def process_file_task(
        self, file_data: FileData, message_text: str
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

    async def ask_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        query = update.callback_query
        if query is not None:
            await query.delete_message()

        return await self.ask_task_helper(
            self.language_service, update, context, self.get_task_data_list()
        )

    async def process_file(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str | int:
        _ = self.language_service.set_app_language(update, context)
        query: CallbackQuery | None = update.callback_query
        message: Message = update.effective_message  # type: ignore

        if query is not None:
            file_data = query.data
            if not isinstance(file_data, FileData):
                raise ValueError(f"Unknown query data type: {type(query.data)}")

            await query.answer()
            await query.edit_message_text(_("Processing your file"))
            context.drop_callback_data(query)
        else:
            try:
                file_data = self.telegram_service.get_file_data(context)  # type: ignore
            except TelegramGetUserDataError as e:
                await message.reply_text(_(str(e)))
                return ConversationHandler.END

        # Delete the previous message and send processing message for processors with
        # nested conversation
        await self._process_previous_message(update, context)

        try:
            async with self.process_file_task(
                file_data, message.text  # type: ignore
            ) as out_path:
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
                return await error_handler(update, context, e, file_data)  # type: ignore
        return ConversationHandler.END

    async def _process_previous_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        message_data = None
        try:
            message_data = self.telegram_service.get_message_data(context)
            await context.bot.delete_message(
                message_data.chat_id, message_data.message_id
            )
        except (TelegramGetUserDataError, BadRequest):
            pass

        if message_data is None:
            return

        _ = self.language_service.set_app_language(update, context)
        await context.bot.send_message(message_data.chat_id, _("Processing your file"))

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
        _file_data: FileData,
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        await update.effective_message.reply_text(_(str(exception)))  # type: ignore
        return ConversationHandler.END
