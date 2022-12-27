import re
from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator

from telegram import Message, Update
from telegram.ext import (
    BaseHandler,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
)

from pdf_bot.analytics import TaskType
from pdf_bot.consts import TEXT_FILTER
from pdf_bot.file_processor import AbstractFileTaskProcessor
from pdf_bot.models import FileData, TaskData
from pdf_bot.telegram_internal import BackData

from .abstract_pdf_processor import AbstractPdfProcessor


class RenamePdfData(FileData):
    pass


class RenamePdfProcessor(AbstractPdfProcessor):
    WAIT_FILE_NAME = "wait_file_name"
    INVALID_CHARACTERS = r"\/*?:\'<>|"

    @property
    def task_type(self) -> TaskType:
        return TaskType.rename_pdf

    @property
    def task_data(self) -> TaskData | None:
        return TaskData(_("Rename"), RenamePdfData)

    @property
    def should_process_back_option(self) -> bool:
        return False

    @property
    def handler(self) -> BaseHandler | None:
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.ask_file_name, pattern=RenamePdfData)
            ],
            states={
                self.WAIT_FILE_NAME: [
                    MessageHandler(TEXT_FILTER, self.rename_pdf),
                    CallbackQueryHandler(self.ask_task, pattern=BackData),
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.telegram_service.cancel_conversation)
            ],
            map_to_parent={
                # Return to wait file task state
                AbstractFileTaskProcessor.WAIT_FILE_TASK: AbstractFileTaskProcessor.WAIT_FILE_TASK,
            },
        )

    @asynccontextmanager
    async def process_file_task(
        self, file_id: str, message_text: str
    ) -> AsyncGenerator[str, None]:
        file_name = re.sub(r"\.pdf$", "", message_text)
        async with self.pdf_service.rename_pdf(file_id, f"{file_name}.pdf") as path:
            yield path

    async def ask_file_name(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        query = update.callback_query
        await query.answer()

        _ = self.language_service.set_app_language(update, context)
        reply_markup = self.telegram_service.get_back_inline_markup(update, context)

        message = await query.edit_message_text(
            _("Send me the file name that you'll like to rename your PDF file into"),
            reply_markup=reply_markup,
        )
        self.telegram_service.cache_message_data(context, message)

        return self.WAIT_FILE_NAME

    async def rename_pdf(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str | int:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.effective_message  # type: ignore
        text = re.sub(r"\.pdf$", "", message.text)

        if set(text) & set(self.INVALID_CHARACTERS):
            await message.reply_text(
                "{desc_1}\n{invalid_chars}\n{desc_2}".format(
                    desc_1=_(
                        "File names can't contain any of the following characters:"
                    ),
                    invalid_chars=self.INVALID_CHARACTERS,
                    desc_2=_("Please try again"),
                ),
            )
            return self.WAIT_FILE_NAME

        return await self.process_file(update, context)
