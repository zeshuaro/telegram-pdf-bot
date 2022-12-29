from abc import abstractmethod
from dataclasses import dataclass
from typing import Callable

from telegram import Message, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
)

from pdf_bot.consts import TEXT_FILTER
from pdf_bot.file_processor import AbstractFileTaskProcessor
from pdf_bot.models import FileData
from pdf_bot.telegram_internal import BackData

from .abstract_pdf_processor import AbstractPdfProcessor


@dataclass(kw_only=True)
class TextInputData(FileData):
    text: str


class AbstractPdfTextInputProcessor(AbstractPdfProcessor):
    WAIT_TEXT_INPUT = "wait_text_input"

    @property
    @abstractmethod
    def entry_point_data_type(self) -> type[FileData]:
        pass

    @abstractmethod
    def get_ask_text_input_text(self, _: Callable[[str], str]) -> str:
        pass

    @abstractmethod
    def get_cleaned_text_input(self, text: str) -> str | None:
        pass

    @property
    @abstractmethod
    def invalid_text_input_error(self) -> str:
        pass

    @property
    def handler(self) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    self._ask_text_input, pattern=self.entry_point_data_type
                )
            ],
            states={
                self.WAIT_TEXT_INPUT: [
                    MessageHandler(TEXT_FILTER, self._process_text_input),
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

    async def _ask_text_input(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        query = update.callback_query
        await query.answer()

        _ = self.language_service.set_app_language(update, context)
        reply_markup = self.telegram_service.get_back_inline_markup(update, context)
        message = await query.edit_message_text(
            self.get_ask_text_input_text(_),
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
        self.telegram_service.cache_message_data(context, message)

        return self.WAIT_TEXT_INPUT

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
        text_input_data = TextInputData(
            id=file_data.id, name=file_data.name, text=cleaned_text
        )
        self.telegram_service.cache_file_data(context, text_input_data)

        return await self.process_file(update, context)
