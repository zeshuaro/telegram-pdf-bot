from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from gettext import gettext as _
from typing import AsyncGenerator

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ParseMode
from telegram.ext import (
    BaseHandler,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
)

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, TEXT_FILTER
from pdf_bot.file_processor import AbstractFileTaskProcessor
from pdf_bot.models import FileData, TaskData
from pdf_bot.pdf import ScaleData
from pdf_bot.telegram_internal import BackData

from .abstract_pdf_processor import AbstractPdfProcessor


class ScalePdfType(Enum):
    by_factor = _("By factor")
    to_dimension = _("To dimension")

    @property
    def ask_value_text(self) -> str:  # pragma: no cover
        match self:
            case ScalePdfType.by_factor:
                return _(
                    "Send me the scaling factors for the horizontal and vertical"
                    " axes\n\nExample: 2 0.5 - this will double the horizontal axis and"
                    " halve the vertical axis"
                )
            case ScalePdfType.to_dimension:
                return _(
                    "Send me the width and height\n\nExample: 150 200 - this will set"
                    " the width to 150 and height to 200"
                )


class ScalePdfData(FileData):
    ...


@dataclass(kw_only=True)
class ScaleTypeData(ScalePdfData):
    scale_type: ScalePdfType


@dataclass(kw_only=True)
class ScaleTypeAndValueData(ScaleTypeData):
    scale_value: ScaleData


class ScalePdfProcessor(AbstractPdfProcessor):
    BY_SCALING_FACTOR = _("By scaling factor")
    TO_DIMENSION = _("To dimension")

    WAIT_SCALE_TYPE = "wait_scale_type"
    WAIT_SCALE_VALUE = "wait_scale_value"

    @property
    def task_type(self) -> TaskType:
        return TaskType.scale_pdf

    @property
    def task_data(self) -> TaskData | None:
        return TaskData(_("Scale"), ScalePdfData)

    @property
    def handler(self) -> BaseHandler | None:
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.ask_scale_type, pattern=ScalePdfData)
            ],
            states={
                self.WAIT_SCALE_TYPE: [
                    CallbackQueryHandler(self.ask_scale_value, pattern=ScaleTypeData),
                    CallbackQueryHandler(self.ask_task, pattern=BackData),
                ],
                self.WAIT_SCALE_VALUE: [
                    MessageHandler(TEXT_FILTER, self.scale_pdf),
                    CallbackQueryHandler(self.ask_scale_type, pattern=ScalePdfData),
                ],
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
        self, file_data: FileData, _message_text: str
    ) -> AsyncGenerator[str, None]:
        if not isinstance(file_data, ScaleTypeAndValueData):
            raise TypeError(f"Invalid file data type: {type(file_data)}")

        match file_data.scale_type:
            case ScalePdfType.by_factor:
                async with self.pdf_service.scale_pdf_by_factor(
                    file_data.id, file_data.scale_value
                ) as path:
                    yield path
            case ScalePdfType.to_dimension:
                async with self.pdf_service.scale_pdf_to_dimension(
                    file_data.id, file_data.scale_value
                ) as path:
                    yield path

    async def ask_scale_type(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        query = update.callback_query
        await query.answer()
        data = query.data

        if not isinstance(data, ScalePdfData):
            raise TypeError(f"Invalid callback query data type: {type(data)}")

        self.telegram_service.cache_file_data(context, data)
        _ = self.language_service.set_app_language(update, context)

        reply_markup = self._get_ask_scale_type_markup(update, context, data)
        await query.edit_message_text(
            _("Select the scale type that you'll like to perform"),
            reply_markup=reply_markup,
        )

        return self.WAIT_SCALE_TYPE

    async def ask_scale_value(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        query = update.callback_query
        await query.answer()
        data = query.data

        if not isinstance(data, ScaleTypeData):
            raise TypeError(f"Invalid callback query data type: {type(data)}")

        self.telegram_service.cache_file_data(context, data)
        _ = self.language_service.set_app_language(update, context)

        reply_markup = self._get_ask_scale_value_markup(update, context, data)
        message = await query.edit_message_text(
            _(data.scale_type.ask_value_text), reply_markup=reply_markup
        )
        self.telegram_service.cache_message_data(context, message)

        return self.WAIT_SCALE_VALUE

    async def scale_pdf(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str | int:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.effective_message  # type: ignore
        text = message.text

        try:
            scale_data = ScaleData.from_string(text)
        except ValueError:
            await message.reply_text(
                _("The values {values} are invalid, please try again").format(
                    values=f"<b>{text}</b>"
                ),
                parse_mode=ParseMode.HTML,
            )
            return self.WAIT_SCALE_VALUE

        file_data = self.telegram_service.get_file_data(context)
        if not isinstance(file_data, ScaleTypeData):
            raise TypeError(f"Invalid callback query data: {file_data}")

        self.telegram_service.cache_file_data(
            context,
            ScaleTypeAndValueData(
                id=file_data.id,
                name=file_data.name,
                scale_type=file_data.scale_type,
                scale_value=scale_data,
            ),
        )

        return await self.process_file(update, context)

    def _get_ask_scale_type_markup(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        scale_data: ScalePdfData,
    ) -> InlineKeyboardMarkup:
        back_button = self.telegram_service.get_back_button(update, context)
        keyboard = [
            [
                InlineKeyboardButton(
                    _(scale_type.value),
                    callback_data=ScaleTypeData(
                        id=scale_data.id, name=scale_data.name, scale_type=scale_type
                    ),
                )
                for scale_type in ScalePdfType
            ],
            [back_button],
        ]

        return InlineKeyboardMarkup(keyboard)

    def _get_ask_scale_value_markup(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        scale_data: ScaleTypeData,
    ) -> InlineKeyboardMarkup:
        _ = self.language_service.set_app_language(update, context)
        keyboard = [
            [
                InlineKeyboardButton(
                    _(BACK), callback_data=ScalePdfData(scale_data.id, scale_data.name)
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
