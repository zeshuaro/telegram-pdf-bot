from contextlib import asynccontextmanager
from gettext import gettext as _
from typing import AsyncGenerator

from telegram import Message, Update
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
from pdf_bot.consts import TEXT_FILTER
from pdf_bot.file_processor import AbstractFileTaskProcessor
from pdf_bot.models import FileData, TaskData
from pdf_bot.telegram_internal import BackData

from .abstract_pdf_processor import AbstractPdfProcessor


class SplitPdfData(FileData):
    pass


class SplitPdfProcessor(AbstractPdfProcessor):
    WAIT_SPLIT_RANGE = "wait_split_range"

    @property
    def task_type(self) -> TaskType:
        return TaskType.split_pdf

    @property
    def task_data(self) -> TaskData | None:
        return TaskData(_("Split"), SplitPdfData)

    @property
    def should_process_back_option(self) -> bool:
        return False

    @property
    def handler(self) -> BaseHandler | None:
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.ask_split_range, pattern=SplitPdfData)
            ],
            states={
                self.WAIT_SPLIT_RANGE: [
                    MessageHandler(TEXT_FILTER, self.split_pdf),
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
        async with self.pdf_service.split_pdf(file_data.id, message_text) as path:
            yield path

    async def ask_split_range(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        query = update.callback_query
        await query.answer()
        _ = self.language_service.set_app_language(update, context)
        reply_markup = self.telegram_service.get_back_inline_markup(update, context)

        # "{intro}\n\n"
        # "<b>{general}</b>\n"
        # "<code>:      {all}</code>\n"
        # "<code>7      {eight_only}</code>\n"
        # "<code>0:3    {first_three}</code>\n"
        # "<code>7:     {from_eight}</code>\n"
        # "<code>-1     {last_only}</code>\n"
        # "<code>:-1    {all_except_last}</code>\n"
        # "<code>-2     {second_last}</code>\n"
        # "<code>-2:    {last_two}</code>\n"
        # "<code>-3:-1  {third_second}</code>\n\n"
        # "<b>{advanced}</b>\n"
        # "<code>::2    {pages} 0 2 4 ... {to_end}</code>\n"
        # "<code>1:10:2 {pages} 1 3 5 7 9</code>\n"
        # "<code>::-1   {all_reversed}</code>\n"
        # "<code>3:0:-1 {pages} 3 2 1 {except_txt} 0</code>\n"
        # "<code>2::-1  {pages} 2 1 0</code>"
        text = (
            "{intro}\n\n"
            "<b>{general}</b>\n"
            "<code>{all}</code>\n"
            "<code>{eight_only}</code>\n"
            "<code>{first_three}</code>\n"
            "<code>{from_eight}</code>\n"
            "<code>{last_only}</code>\n"
            "<code>{all_except_last}</code>\n"
            "<code>{second_last}</code>\n"
            "<code>{last_two}</code>\n"
            "<code>{third_second}</code>\n\n"
            "<b>{advanced}</b>\n"
            "<code>{pages_to_end}</code>\n"
            "<code>{odd_pages}</code>\n"
            "<code>{all_reversed}</code>\n"
            "<code>{pages_except}</code>\n"
            "<code>{pages_reverse_from}</code>"
        ).format(
            intro=_("Send me the range of pages that you'll like to keep"),
            general=_("General usage"),
            all=_("{range}      all pages").format(range=":"),
            eight_only=_("{range}      page 8 only").format(range="7"),
            first_three=_("{range}    first three pages").format(range="0:3"),
            from_eight=_("{range}     from page 8 onward").format(range="7:"),
            last_only=_("{range}     last page only").format(range="-1"),
            all_except_last=_("{range}    all pages except the last page").format(
                range=":-1"
            ),
            second_last=_("{range}     second last page only").format(range="-2"),
            last_two=_("{range}    last two pages").format(range="-2:"),
            third_second=_("{range}  third and second last pages").format(
                range="-3:-1"
            ),
            advanced=_("Advanced usage"),
            pages_to_end=_("{range}    pages {pages} and to the end").format(
                range="::2", pages="0 2 4 ..."
            ),
            odd_pages=_("{range} pages {pages}").format(
                range="1:10:2", pages="1 3 5 7 9"
            ),
            all_reversed=_("{range}   all pages in reversed order").format(
                range="::-1"
            ),
            pages_except=_("{range} pages {pages} except {page}").format(
                range="3:0:-1", pages="3 2 1", page="0"
            ),
            pages_reverse_from=_("{range}  pages {pages}").format(
                range="2::-1", pages="2 1 0"
            ),
        )
        message = await query.edit_message_text(
            text, parse_mode=ParseMode.HTML, reply_markup=reply_markup
        )
        self.telegram_service.cache_message_data(context, message)

        return self.WAIT_SPLIT_RANGE

    async def split_pdf(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str | int:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.effective_message  # type: ignore
        text = message.text

        if not self.pdf_service.split_range_valid(text):
            await message.reply_text(_("The range is invalid, please try again"))
            return self.WAIT_SPLIT_RANGE

        return await self.process_file(update, context)
