from gettext import gettext as _
from typing import cast

from telegram import Document, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import CANCEL, DONE
from pdf_bot.language import LanguageService
from pdf_bot.models import FileData
from pdf_bot.pdf import PdfService, PdfServiceError
from pdf_bot.telegram_internal import TelegramService, TelegramServiceError


class MergeService:
    WAIT_MERGE_PDF = 0
    _MERGE_PDF_DATA = "merge_pdf_data"
    _REMOVE_LAST = _("Remove last file")

    def __init__(
        self,
        pdf_service: PdfService,
        telegram_service: TelegramService,
        language_service: LanguageService,
    ) -> None:
        self.pdf_service = pdf_service
        self.telegram_service = telegram_service
        self.language_service = language_service

    async def ask_first_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        self.telegram_service.update_user_data(context, self._MERGE_PDF_DATA, [])
        _ = self.language_service.set_app_language(update, context)
        await self.telegram_service.reply_with_cancel_markup(
            update,
            context,
            "{desc_1}\n\n{desc_2}".format(
                desc_1=_("Send me the PDF files that you'll like to merge"),
                desc_2=_("Note that the files will be merged in the order that you send me"),
            ),
        )

        return self.WAIT_MERGE_PDF

    async def check_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        _ = self.language_service.set_app_language(update, context)
        msg = cast(Message, update.effective_message)

        try:
            doc = self.telegram_service.check_pdf_document(msg)
        except TelegramServiceError as e:
            await msg.reply_text(_(str(e)))
            return self.WAIT_MERGE_PDF

        try:
            self._append_file_data(context, doc)
        except TelegramServiceError as e:
            await msg.reply_text(_(str(e)))
            return ConversationHandler.END

        return await self._ask_next_pdf(update, context)

    async def check_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        _ = self.language_service.set_app_language(update, context)
        msg = cast(Message, update.effective_message)
        text = msg.text

        if text in [_(self._REMOVE_LAST), _(DONE)]:
            try:
                file_data_list = self.telegram_service.get_user_data(context, self._MERGE_PDF_DATA)
            except TelegramServiceError as e:
                await msg.reply_text(_(str(e)))
                return ConversationHandler.END

            if text == _(self._REMOVE_LAST):
                return await self._remove_last_pdf(update, context, file_data_list)
            return await self._preprocess_pdfs(update, context, file_data_list)
        if text == _(CANCEL):
            return await self.telegram_service.cancel_conversation(update, context)
        return self.WAIT_MERGE_PDF

    async def _ask_next_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        _ = self.language_service.set_app_language(update, context)
        msg = cast(Message, update.effective_message)
        text = "{desc}\n".format(desc=_("You've sent me these PDF files so far:"))
        await self.telegram_service.send_file_names(
            msg.chat_id,
            text,
            context.user_data[self._MERGE_PDF_DATA],  # type: ignore[index]
        )

        reply_markup = ReplyKeyboardMarkup(
            [[_(DONE)], [_(self._REMOVE_LAST), _(CANCEL)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await msg.reply_text(
            _(
                "Press {done} if you've sent me all the PDF files that "
                "you'll like to merge or keep sending me the PDF files"
            ).format(done=f"<b>{_(DONE)}</b>"),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )

        return self.WAIT_MERGE_PDF

    async def _remove_last_pdf(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        file_data_list: list[FileData],
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        msg = cast(Message, update.effective_message)

        try:
            file_data = file_data_list.pop()
        except IndexError:
            await msg.reply_text(_("You've already removed all the PDF files you've sent me"))
            return await self.ask_first_pdf(update, context)

        await msg.reply_text(
            _("{file_name} has been removed for merging").format(
                file_name=f"<b>{file_data.name}</b>"
            ),
            parse_mode=ParseMode.HTML,
        )

        if file_data_list:
            self.telegram_service.update_user_data(context, self._MERGE_PDF_DATA, file_data_list)
            return await self._ask_next_pdf(update, context)
        return await self.ask_first_pdf(update, context)

    async def _preprocess_pdfs(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        file_data_list: list[FileData],
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        msg = cast(Message, update.effective_message)
        num_files = len(file_data_list)

        if num_files == 0:
            await msg.reply_text(_("You haven't sent me any PDF files"))
            return await self.ask_first_pdf(update, context)
        if num_files == 1:
            await msg.reply_text(_("You've only sent me one PDF file"))
            self.telegram_service.update_user_data(context, self._MERGE_PDF_DATA, file_data_list)
            return await self._ask_next_pdf(update, context)
        return await self._merge_pdfs(update, context, file_data_list)

    async def _merge_pdfs(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        file_data_list: list[FileData],
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        msg = cast(Message, update.effective_message)
        await msg.reply_text(_("Merging your PDF files"), reply_markup=ReplyKeyboardRemove())

        try:
            async with self.pdf_service.merge_pdfs(file_data_list) as out_path:
                await self.telegram_service.send_file(update, context, out_path, TaskType.merge_pdf)
        except PdfServiceError as e:
            await msg.reply_text(_(str(e)))

        return ConversationHandler.END

    def _append_file_data(self, context: ContextTypes.DEFAULT_TYPE, document: Document) -> None:
        file_data_list: list[FileData] = self.telegram_service.get_user_data(
            context, self._MERGE_PDF_DATA
        )
        file_data = FileData.from_telegram_object(document)
        file_data_list.append(file_data)
        self.telegram_service.update_user_data(context, self._MERGE_PDF_DATA, file_data_list)
