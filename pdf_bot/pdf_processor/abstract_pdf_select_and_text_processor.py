from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
)

from pdf_bot.consts import BACK, TEXT_FILTER
from pdf_bot.file_processor import AbstractFileTaskProcessor
from pdf_bot.models import FileData
from pdf_bot.telegram_internal import BackData

from .abstract_pdf_processor import AbstractPdfProcessor


class SelectOption(Enum):
    @property
    @abstractmethod
    def ask_value_text(self) -> str:
        pass


@dataclass(kw_only=True)
class SelectOptionData(FileData):
    option: SelectOption


@dataclass(kw_only=True)
class OptionAndInputData(SelectOptionData):
    text: str | Any


class AbstractPdfSelectAndTextProcessor(AbstractPdfProcessor):
    WAIT_SELECT_OPTION = "wait_select_option"
    WAIT_TEXT_INPUT = "wait_text_input"

    @property
    @abstractmethod
    def entry_point_data_type(self) -> type[FileData]:
        pass

    @property
    @abstractmethod
    def ask_select_option_text(self) -> str:
        pass

    @property
    @abstractmethod
    def select_option_type(self) -> type[SelectOption]:
        pass

    @abstractmethod
    def get_cleaned_text_input(self, text: str) -> str | Any | None:
        pass

    @property
    @abstractmethod
    def invalid_text_input_error(self) -> str:
        pass

    @property
    def option_and_input_data_type(self) -> type[OptionAndInputData]:
        return OptionAndInputData

    @property
    def handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    self._ask_select_option, pattern=self.entry_point_data_type
                )
            ],
            states={
                self.WAIT_SELECT_OPTION: [
                    CallbackQueryHandler(
                        self._ask_text_input, pattern=SelectOptionData
                    ),
                    CallbackQueryHandler(self.ask_task, pattern=BackData),
                ],
                self.WAIT_TEXT_INPUT: [
                    MessageHandler(TEXT_FILTER, self._process_text_input),
                    CallbackQueryHandler(
                        self._ask_select_option, pattern=self.entry_point_data_type
                    ),
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

    async def _ask_select_option(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        query = update.callback_query
        await query.answer()
        data: FileData = query.data  # type: ignore

        self.telegram_service.cache_file_data(context, data)
        _ = self.language_service.set_app_language(update, context)

        reply_markup = self._get_ask_select_option_markup(update, context, data)
        await query.edit_message_text(
            _(self.ask_select_option_text), reply_markup=reply_markup
        )

        return self.WAIT_SELECT_OPTION

    def _get_ask_select_option_markup(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        query_data: FileData,
    ) -> InlineKeyboardMarkup:
        _ = self.language_service.set_app_language(update, context)
        back_button = self.telegram_service.get_back_button(update, context)

        keyboard = [
            [
                InlineKeyboardButton(
                    _(option.value),
                    callback_data=SelectOptionData(
                        id=query_data.id, name=query_data.name, option=option
                    ),
                )
                for option in self.select_option_type
            ],
            [back_button],
        ]

        return InlineKeyboardMarkup(keyboard)

    async def _ask_text_input(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        query = update.callback_query
        await query.answer()
        data = query.data

        if not isinstance(data, SelectOptionData):
            raise TypeError(f"Invalid callback query data type: {type(data)}")

        self.telegram_service.cache_file_data(context, data)
        _ = self.language_service.set_app_language(update, context)

        reply_markup = self._get_ask_text_input_markup(update, context, data)
        message = await query.edit_message_text(
            _(data.option.ask_value_text), reply_markup=reply_markup
        )
        self.telegram_service.cache_message_data(context, message)

        return self.WAIT_TEXT_INPUT

    def _get_ask_text_input_markup(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        query_data: FileData,
    ) -> InlineKeyboardMarkup:
        _ = self.language_service.set_app_language(update, context)
        keyboard = [
            [
                InlineKeyboardButton(
                    _(BACK),
                    callback_data=self.entry_point_data_type(
                        query_data.id, query_data.name
                    ),
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _process_text_input(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str | int:
        message: Message = update.effective_message  # type: ignore
        cleaned_text = self.get_cleaned_text_input(message.text)

        if cleaned_text is None:
            _ = self.language_service.set_app_language(update, context)
            await message.reply_text(_(self.invalid_text_input_error))
            return self.WAIT_TEXT_INPUT

        file_data = self.telegram_service.get_file_data(context)
        if not isinstance(file_data, SelectOptionData):
            raise TypeError(f"Invalid callback query data: {file_data}")

        option_input_data = self.option_and_input_data_type(
            id=file_data.id,
            name=file_data.name,
            option=file_data.option,
            text=cleaned_text,
        )
        self.telegram_service.cache_file_data(context, option_input_data)

        return await self.process_file(update, context)
