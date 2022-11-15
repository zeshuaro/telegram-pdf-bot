from pdf_diff import NoDifferenceError
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import BACK, CANCEL
from pdf_bot.language_new import LanguageService
from pdf_bot.pdf import PdfService
from pdf_bot.telegram_internal import (
    TelegramService,
    TelegramServiceError,
    TelegramUserDataKeyError,
)


class CompareService:
    WAIT_FIRST_PDF = 0
    WAIT_SECOND_PDF = 1
    _COMPARE_ID = "compare_id"

    def __init__(
        self,
        pdf_service: PdfService,
        telegram_service: TelegramService,
        language_service: LanguageService,
    ) -> None:
        self.pdf_service = pdf_service
        self.telegram_service = telegram_service
        self.language_service = language_service

    def ask_first_pdf(self, update: Update, context: CallbackContext) -> int:
        _ = self.language_service.set_app_language(update, context)
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

        return self.WAIT_FIRST_PDF

    def check_first_pdf(self, update: Update, context: CallbackContext) -> int:
        _ = self.language_service.set_app_language(update, context)
        message = update.effective_message

        try:
            doc = self.telegram_service.check_pdf_document(message)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return self.WAIT_FIRST_PDF

        context.user_data[self._COMPARE_ID] = doc.file_id
        reply_markup = ReplyKeyboardMarkup(
            [[_(BACK), _(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
        )
        message.reply_text(
            _("Send me the other PDF file that you'll like to compare"),
            reply_markup=reply_markup,
        )

        return self.WAIT_SECOND_PDF

    def compare_pdfs(self, update: Update, context: CallbackContext) -> int:
        _ = self.language_service.set_app_language(update, context)
        message = update.effective_message

        try:
            doc = self.telegram_service.check_pdf_document(message)
            file_id = self.telegram_service.get_user_data(context, self._COMPARE_ID)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            if isinstance(e, TelegramUserDataKeyError):
                return ConversationHandler.END
            return self.WAIT_SECOND_PDF

        message.reply_text(
            _("Comparing your PDF files"), reply_markup=ReplyKeyboardRemove()
        )

        try:
            with self.pdf_service.compare_pdfs(file_id, doc.file_id) as out_path:
                self.telegram_service.reply_with_file(
                    update, context, out_path, TaskType.compare_pdf
                )
        except NoDifferenceError:
            message.reply_text(
                _("There are no text differences between your PDF files")
            )

        return ConversationHandler.END

    def check_text(self, update: Update, context: CallbackContext) -> int | None:
        _ = self.language_service.set_app_language(update, context)
        text = update.effective_message.text

        if text == _(BACK):
            return self.ask_first_pdf(update, context)
        if text == _(CANCEL):
            return self.telegram_service.cancel_conversation(update, context)

        return None
