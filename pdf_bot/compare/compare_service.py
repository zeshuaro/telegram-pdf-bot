from pdf_diff import NoDifferenceError
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.compare.constants import COMPARE_ID, WAIT_FIRST_PDF, WAIT_SECOND_PDF
from pdf_bot.consts import BACK, CANCEL, PDF_INVALID_FORMAT, PDF_OK
from pdf_bot.language import set_lang
from pdf_bot.pdf import PdfService
from pdf_bot.utils import cancel, check_pdf, check_user_data, send_result_file


class CompareService:
    def __init__(self, pdf_service: PdfService) -> None:
        self.pdf_service = pdf_service

    @staticmethod
    def ask_first_pdf(update: Update, context: CallbackContext) -> int:
        _ = set_lang(update, context)
        reply_markup = ReplyKeyboardMarkup(
            [[_(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
        )
        update.effective_message.reply_text(
            "{desc_1}\n\n{desc_2}".format(
                desc_1=_("Send me one of the PDF files that you'll like to compare"),
                desc_2=_("Note that I can only look for text differences"),
            ),
            reply_markup=reply_markup,
        )

        return WAIT_FIRST_PDF

    @staticmethod
    def check_first_pdf(update: Update, context: CallbackContext) -> int:
        result = check_pdf(update, context)
        if result == PDF_INVALID_FORMAT:
            return WAIT_FIRST_PDF
        if result != PDF_OK:
            return ConversationHandler.END

        _ = set_lang(update, context)
        context.user_data[COMPARE_ID] = update.effective_message.document.file_id

        reply_markup = ReplyKeyboardMarkup(
            [[_(BACK), _(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
        )
        update.effective_message.reply_text(
            _("Send me the other PDF file that you'll like to compare"),
            reply_markup=reply_markup,
        )

        return WAIT_SECOND_PDF

    def check_second_pdf(self, update: Update, context: CallbackContext) -> int:
        if not check_user_data(update, context, COMPARE_ID):
            return ConversationHandler.END

        result = check_pdf(update, context)
        if result == PDF_INVALID_FORMAT:
            return WAIT_SECOND_PDF
        if result != PDF_OK:
            return ConversationHandler.END

        return self.compare_pdfs(update, context)

    def compare_pdfs(self, update: Update, context: CallbackContext) -> int:
        _ = set_lang(update, context)
        message = update.effective_message
        user_data = context.user_data

        message.reply_text(
            _("Comparing your PDF files"), reply_markup=ReplyKeyboardRemove()
        )
        file_id_a = user_data[COMPARE_ID]
        file_id_b = message.document.file_id

        try:
            with self.pdf_service.compare_pdfs(file_id_a, file_id_b) as out_fn:
                send_result_file(update, context, out_fn, TaskType.compare_pdf)
        except NoDifferenceError:
            message.reply_text(
                _("There are no text differences between your PDF files")
            )

        if user_data[COMPARE_ID] == file_id_a:
            del user_data[COMPARE_ID]

        return ConversationHandler.END

    def check_text(self, update: Update, context: CallbackContext) -> int | None:
        _ = set_lang(update, context)
        text = update.effective_message.text

        if text == _(BACK):
            return self.ask_first_pdf(update, context)
        if text == _(CANCEL):
            return cancel(update, context)

        return None
