from contextlib import asynccontextmanager
from dataclasses import dataclass
from gettext import gettext as _
from typing import AsyncGenerator

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

from pdf_bot.analytics import TaskType
from pdf_bot.file_processor import AbstractFileTaskProcessor
from pdf_bot.models import FileData, TaskData
from pdf_bot.telegram_internal import BackData

from .abstract_pdf_processor import AbstractPdfProcessor


class RotatePdfData(FileData):
    ...


@dataclass(kw_only=True)
class RotateDegreeData(RotatePdfData):
    degree: int


class RotatePdfProcessor(AbstractPdfProcessor):
    _WAIT_DEGREE = "wait_degree"
    _DEGREES = [90, 180, 270]

    @property
    def task_type(self) -> TaskType:
        return TaskType.rotate_pdf

    @property
    def task_data(self) -> TaskData:
        return TaskData(_("Rotate"), RotatePdfData)

    @property
    def handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[CallbackQueryHandler(self.ask_degree, pattern=RotatePdfData)],
            states={
                self._WAIT_DEGREE: [
                    CallbackQueryHandler(self.process_file, pattern=RotateDegreeData),
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
        self, file_data: FileData, message_text: str
    ) -> AsyncGenerator[str, None]:
        if not isinstance(file_data, RotateDegreeData):
            raise TypeError(f"Invalid file data type: {type(file_data)}")

        async with self.pdf_service.rotate_pdf(file_data.id, file_data.degree) as path:
            yield path

    async def ask_degree(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        query = update.callback_query
        await query.answer()
        data = query.data

        if not isinstance(data, RotatePdfData):
            raise TypeError(f"Invalid callback query data type: {type(data)}")

        reply_markup = self._get_ask_degree_reply_markup(update, context, data)
        _ = self.language_service.set_app_language(update, context)
        await query.edit_message_text(
            _(
                "Select the degrees that you'll like to rotate your PDF file in"
                " clockwise"
            ),
            reply_markup=reply_markup,
        )

        return self._WAIT_DEGREE

    def _get_ask_degree_reply_markup(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        rotate_data: RotatePdfData,
    ) -> InlineKeyboardMarkup:
        back_button = self.telegram_service.get_back_button(update, context)
        keyboard = [
            [
                InlineKeyboardButton(
                    str(degree),
                    callback_data=RotateDegreeData(
                        id=rotate_data.id, name=rotate_data.name, degree=degree
                    ),
                )
                for degree in self._DEGREES
            ],
            [back_button],
        ]

        return InlineKeyboardMarkup(keyboard)
