import re
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from telegram import Message, Update
from telegram.ext import ContextTypes

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK

from .abstract_pdf_processor import AbstractPdfProcessor


class RenamePdfProcessor(AbstractPdfProcessor):
    WAIT_NEW_FILE_NAME = "wait_new_file_name"
    INVALID_CHARACTERS = r"\/*?:\'<>|"

    @property
    def task_type(self) -> TaskType:
        return TaskType.rename_pdf

    @property
    def should_process_back_option(self) -> bool:
        return False

    @asynccontextmanager
    async def process_file_task(
        self, file_id: str, message_text: str
    ) -> AsyncGenerator[str, None]:
        file_name = re.sub(r"\.pdf$", "", message_text)
        async with self.pdf_service.rename_pdf(file_id, f"{file_name}.pdf") as path:
            yield path

    async def ask_new_file_name(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        _ = self.language_service.set_app_language(update, context)
        await self.telegram_service.reply_with_back_markup(
            update,
            context,
            _("Send me the file name that you'll like to rename your PDF file into"),
        )
        return self.WAIT_NEW_FILE_NAME

    async def rename_pdf(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str | int:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.message

        if message.text == _(BACK):
            return await self.file_task_service.ask_pdf_task(update, context)

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
            return self.WAIT_NEW_FILE_NAME

        return await self.process_file(update, context)
