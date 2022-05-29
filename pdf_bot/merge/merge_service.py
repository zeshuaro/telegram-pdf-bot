from typing import List

from telegram import (
    ChatAction,
    ParseMode,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import CANCEL, DONE, PDF_INVALID_FORMAT, PDF_TOO_LARGE, REMOVE_LAST
from pdf_bot.language import set_lang
from pdf_bot.merge.constants import MERGE_PDF_DATA, WAIT_MERGE_PDF
from pdf_bot.models import FileData
from pdf_bot.pdf import PdfService, PdfServiceError
from pdf_bot.telegram import TelegramService
from pdf_bot.utils import (
    cancel,
    check_pdf,
    check_user_data,
    reply_with_cancel_btn,
    send_result_file,
)


class MergeService:
    def __init__(
        self, pdf_service: PdfService, telegram_service: TelegramService
    ) -> None:
        self.pdf_service = pdf_service
        self.telegram_service = telegram_service

    @staticmethod
    def ask_first_pdf(update: Update, context: CallbackContext) -> int:
        context.user_data[MERGE_PDF_DATA] = []
        _ = set_lang(update, context)

        reply_with_cancel_btn(
            update,
            context,
            "{desc_1}\n\n{desc_2}".format(
                desc_1=_("Send me the PDF files that you'll like to merge"),
                desc_2=_(
                    "Note that the files will be merged in the order that you send me"
                ),
            ),
        )

        return WAIT_MERGE_PDF

    def check_pdf_for_merge(self, update: Update, context: CallbackContext) -> int:
        message = update.effective_message
        message.reply_chat_action(ChatAction.TYPING)
        result = check_pdf(update, context, send_msg=False)

        if result in [PDF_INVALID_FORMAT, PDF_TOO_LARGE]:
            return self.process_invalid_pdf(update, context, result)

        file_data = FileData.from_telegram_document(message.document)
        context.user_data[MERGE_PDF_DATA].append(file_data)
        return self.ask_next_pdf(update, context)

    def process_invalid_pdf(
        self, update: Update, context: CallbackContext, pdf_result: int
    ) -> int:
        _ = set_lang(update, context)
        if pdf_result == PDF_INVALID_FORMAT:
            text = _("Your file is not a PDF file")
        else:
            text = (
                "{desc_1}\n\n{desc_2}".format(
                    desc_1=_("Your file is too large for me to download and process"),
                    desc_2=_(
                        "Note that this is a Telegram Bot limitation and there's "
                        "nothing I can do unless Telegram changes this limit"
                    ),
                ),
            )

        update.effective_message.reply_text(text)
        if not context.user_data[MERGE_PDF_DATA]:
            return self.ask_first_pdf(update, context)
        return self.ask_next_pdf(update, context)

    def ask_next_pdf(self, update: Update, context: CallbackContext) -> int:
        _ = set_lang(update, context)
        text = "{desc}\n".format(desc=_("You've sent me these PDF files so far:"))
        self.telegram_service.send_file_names(
            update.effective_chat.id, text, context.user_data[MERGE_PDF_DATA]
        )

        reply_markup = ReplyKeyboardMarkup(
            [[_(DONE)], [_(REMOVE_LAST), _(CANCEL)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        update.effective_message.reply_text(
            _(
                "Press {done} if you've sent me all the PDF files that "
                "you'll like to merge or keep sending me the PDF files"
            ).format(done=f"<b>{_(DONE)}</b>"),
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )

        return WAIT_MERGE_PDF

    def check_text(self, update: Update, context: CallbackContext) -> int:
        message = update.effective_message
        _ = set_lang(update, context)
        text = message.text

        if text in [_(REMOVE_LAST), _(DONE)]:
            if not check_user_data(update, context, MERGE_PDF_DATA):
                return ConversationHandler.END

            if text == _(REMOVE_LAST):
                return self.remove_last_pdf(update, context)
            if text == _(DONE):
                return self.preprocess_pdfs(update, context)
        elif text == _(CANCEL):
            return cancel(update, context)

        return WAIT_MERGE_PDF

    def remove_last_pdf(self, update: Update, context: CallbackContext) -> int:
        _ = set_lang(update, context)

        file_data_list: List[FileData] = context.user_data[MERGE_PDF_DATA]
        try:
            file_data = file_data_list.pop()
        except IndexError:
            update.effective_message.reply_text(
                _("You've already removed all the PDF files you've sent me")
            )
            return self.ask_first_pdf(update, context)

        update.effective_message.reply_text(
            _("{file_name} has been removed for merging").format(
                file_name=f"<b>{file_data.name}</b>"
            ),
            parse_mode=ParseMode.HTML,
        )

        if file_data_list:
            return self.ask_next_pdf(update, context)
        return self.ask_first_pdf(update, context)

    def preprocess_pdfs(self, update: Update, context: CallbackContext) -> int:
        _ = set_lang(update, context)
        num_files = len(context.user_data[MERGE_PDF_DATA])

        if num_files == 0:
            update.effective_message.reply_text(_("You haven't sent me any PDF files"))
            return self.ask_first_pdf(update, context)
        if num_files == 1:
            update.effective_message.reply_text(_("You've only sent me one PDF file"))
            return self.ask_next_pdf(update, context)
        return self.merge_pdfs(update, context)

    def merge_pdfs(self, update: Update, context: CallbackContext) -> int:
        _ = set_lang(update, context)
        update.effective_message.reply_text(
            _("Merging your PDF files"), reply_markup=ReplyKeyboardRemove()
        )

        try:
            with self.pdf_service.merge_pdfs(
                context.user_data[MERGE_PDF_DATA]
            ) as out_path:
                send_result_file(update, context, out_path, TaskType.merge_pdf)
        except PdfServiceError as e:
            update.effective_message.reply_text(_(e))

        context.user_data[MERGE_PDF_DATA] = []
        return ConversationHandler.END
