from pdf_diff import NoDifferenceError
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.compare.constants import COMPARE_ID, WAIT_FIRST_PDF, WAIT_SECOND_PDF
from pdf_bot.consts import BACK, CANCEL
from pdf_bot.language import set_lang
from pdf_bot.pdf import PdfService
from pdf_bot.telegram import (
    TelegramService,
    TelegramServiceError,
    TelegramUserDataKeyError,
)
from pdf_bot.utils import cancel, send_result_file


class CompareService:
    def __init__(
        self, pdf_service: PdfService, telegram_service: TelegramService
    ) -> None:
        self.pdf_service = pdf_service
        self.telegram_service = telegram_service

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

    def check_first_pdf(self, update: Update, context: CallbackContext) -> int:
        _ = set_lang(update, context)
        message = update.effective_message

        try:
            doc = self.telegram_service.check_pdf_document(message)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return WAIT_FIRST_PDF

        context.user_data[COMPARE_ID] = doc.file_id
        reply_markup = ReplyKeyboardMarkup(
            [[_(BACK), _(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
        )
        message.reply_text(
            _("Send me the other PDF file that you'll like to compare"),
            reply_markup=reply_markup,
        )

        return WAIT_SECOND_PDF

    def compare_pdfs(self, update: Update, context: CallbackContext) -> int:
        _ = set_lang(update, context)
        message = update.effective_message

        try:
            file_id = self.telegram_service.get_user_data(context, COMPARE_ID)
            doc = self.telegram_service.check_pdf_document(message)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            if isinstance(e, TelegramUserDataKeyError):
                return ConversationHandler.END
            return WAIT_SECOND_PDF

        message.reply_text(
            _("Comparing your PDF files"), reply_markup=ReplyKeyboardRemove()
        )

        try:
            with self.pdf_service.compare_pdfs(file_id, doc.file_id) as out_path:
                send_result_file(update, context, out_path, TaskType.compare_pdf)
        except NoDifferenceError:
            message.reply_text(
                _("There are no text differences between your PDF files")
            )

        return ConversationHandler.END

    def check_text(self, update: Update, context: CallbackContext) -> int | None:
        _ = set_lang(update, context)
        text = update.effective_message.text

        if text == _(BACK):
            return self.ask_first_pdf(update, context)
        if text == _(CANCEL):
            return cancel(update, context)

        return None
