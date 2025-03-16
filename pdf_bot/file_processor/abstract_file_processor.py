import shutil
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Callable, Coroutine, Sequence
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any, ClassVar, cast

from telegram import Message, Update
from telegram.error import BadRequest
from telegram.ext import BaseHandler, ContextTypes, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.errors import CallbackQueryDataTypeError
from pdf_bot.file_processor.errors import DuplicateClassError
from pdf_bot.language import LanguageService
from pdf_bot.models import FileData, FileTaskResult, TaskData
from pdf_bot.telegram_internal import TelegramGetUserDataError, TelegramService

from .file_task_mixin import FileTaskMixin

ErrorHandlerType = Callable[
    [Update, ContextTypes.DEFAULT_TYPE, Exception, FileData],
    Coroutine[Any, Any, str | int],
]


class AbstractFileProcessor(FileTaskMixin, ABC):
    _FILE_PROCESSORS: ClassVar[dict[str, "AbstractFileProcessor"]] = {}

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
            raise DuplicateClassError(cls_name)
        self._FILE_PROCESSORS[cls_name] = self

    @classmethod
    @abstractmethod
    def get_task_data_list(cls) -> Sequence[TaskData]:
        pass

    @classmethod
    def get_handlers(cls) -> list[BaseHandler]:
        return [x.handler for x in cls._FILE_PROCESSORS.values()]

    @property
    @abstractmethod
    def task_type(self) -> TaskType:
        pass

    @property
    @abstractmethod
    def task_data(self) -> TaskData:
        pass

    @property
    @abstractmethod
    def handler(self) -> BaseHandler:
        pass

    @asynccontextmanager
    @abstractmethod
    async def process_file_task(self, file_data: FileData) -> AsyncGenerator[FileTaskResult, None]:
        yield FileTaskResult(Path())

    @property
    def generic_error_types(self) -> set[type[Exception]]:
        return set()

    @property
    def custom_error_handlers(
        self,
    ) -> dict[type[Exception], ErrorHandlerType]:
        return {}

    async def ask_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str | int:
        query = update.callback_query
        if query is not None:
            await query.delete_message()

        return await self.ask_task_helper(
            self.language_service, update, context, self.get_task_data_list()
        )

    async def process_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str | int:
        _ = self.language_service.set_app_language(update, context)
        query = update.callback_query
        msg = cast("Message", update.effective_message)
        file_data: str | FileData

        if query is not None:
            data: str | FileData | None = query.data
            if not isinstance(data, FileData):
                raise CallbackQueryDataTypeError(data)

            file_data = data
            await self.telegram_service.answer_query_and_drop_data(context, query)
            await query.edit_message_text(_("Processing your file"))
        else:
            try:
                file_data = self.telegram_service.get_file_data(context)
            except TelegramGetUserDataError as e:
                await msg.reply_text(_(str(e)))
                return ConversationHandler.END

        # Delete the previous message and send processing message for processors with
        # nested conversation
        await self._process_previous_message(update, context)

        state = await self._process_file_task(update, context, file_data)
        if state is not None:
            return state

        return ConversationHandler.END

    async def _process_file_task(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, file_data: FileData
    ) -> str | int | None:
        try:
            async with self.process_file_task(file_data) as result:
                if result.message is not None:
                    await self.telegram_service.send_message(update, context, result.message)

                out_path = final_path = result.path
                final_path = out_path

                if out_path.is_dir():
                    shutil.make_archive(str(out_path), "zip", out_path)
                    final_path = out_path.with_suffix(".zip")

                await self.telegram_service.send_file(update, context, final_path, self.task_type)
        except Exception as e:
            handlers = self._get_error_handlers()
            error_handler: ErrorHandlerType | None = None
            for error_type, handler in handlers.items():
                if isinstance(e, error_type):
                    error_handler = handler

            if error_handler is not None:
                return await error_handler(update, context, e, file_data)
            raise
        return None

    async def _process_previous_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        message_data = None
        with suppress(TelegramGetUserDataError, BadRequest):
            message_data = self.telegram_service.get_message_data(context)
            await context.bot.delete_message(message_data.chat_id, message_data.message_id)

        if message_data is None:
            return

        _ = self.language_service.set_app_language(update, context)
        await context.bot.send_message(message_data.chat_id, _("Processing your file"))

    def _get_error_handlers(
        self,
    ) -> dict[type[Exception], ErrorHandlerType]:
        handlers: dict[type[Exception], ErrorHandlerType] = dict.fromkeys(
            self.generic_error_types, self._handle_generic_error
        )
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
        msg = cast("Message", update.effective_message)
        await msg.reply_text(_(str(exception)))

        return ConversationHandler.END
