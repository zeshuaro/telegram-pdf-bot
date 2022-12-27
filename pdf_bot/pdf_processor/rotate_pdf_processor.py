from contextlib import asynccontextmanager
from typing import AsyncGenerator

from telegram import Message, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK
from pdf_bot.models import FileData

from .abstract_pdf_processor import AbstractPdfProcessor


class RotatePdfProcessor(AbstractPdfProcessor):
    WAIT_ROTATE_DEGREE = "wait_rotate_degree"
    _ROTATE_90 = "90"
    _ROTATE_180 = "180"
    _ROTATE_270 = "270"

    @property
    def task_type(self) -> TaskType:
        return TaskType.rotate_pdf

    @property
    def should_process_back_option(self) -> bool:
        return False

    @asynccontextmanager
    async def process_file_task(
        self, file_data: FileData, message_text: str
    ) -> AsyncGenerator[str, None]:
        async with self.pdf_service.rotate_pdf(file_data.id, int(message_text)) as path:
            yield path

    async def ask_degree(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        _ = self.language_service.set_app_language(update, context)

        keyboard = [
            [self._ROTATE_90, self._ROTATE_180],
            [self._ROTATE_270, _(BACK)],
        ]
        reply_markup = ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True, one_time_keyboard=True
        )
        await update.effective_message.reply_text(  # type: ignore
            _(
                "Select the degrees that you'll like to "
                "rotate your PDF file in clockwise"
            ),
            reply_markup=reply_markup,
        )

        return self.WAIT_ROTATE_DEGREE

    async def rotate_pdf(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str | int:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.message
        text = message.text

        if text == _(BACK):
            return await self.file_task_service.ask_pdf_task(update, context)
        if text not in {
            self._ROTATE_90,
            self._ROTATE_180,
            self._ROTATE_270,
        }:
            await message.reply_text(_("Invalid rotation degree, try again"))
            return self.WAIT_ROTATE_DEGREE

        return await self.process_file(update, context)
