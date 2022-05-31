from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.chataction import ChatAction
from telegram.ext import CallbackContext, ConversationHandler
from telegram.parsemode import ParseMode

from pdf_bot.analytics import TaskType
from pdf_bot.consts import CANCEL
from pdf_bot.language import set_lang
from pdf_bot.pdf import PdfService
from pdf_bot.telegram import TelegramService, TelegramServiceError
from pdf_bot.text.constants import SKIP, TEXT_KEY, WAIT_FONT, WAIT_TEXT
from pdf_bot.text.models import FontData
from pdf_bot.text.text_repository import TextRepository
from pdf_bot.utils import cancel, send_result_file


class TextService:
    def __init__(
        self,
        text_repository: TextRepository,
        pdf_service: PdfService,
        telegram_service: TelegramService,
    ) -> None:
        self.text_repository = text_repository
        self.pdf_service = pdf_service
        self.telegram_service = telegram_service

    @staticmethod
    def ask_pdf_text(update: Update, context: CallbackContext):
        _ = set_lang(update, context)
        reply_markup = ReplyKeyboardMarkup(
            [[_(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
        )
        update.effective_message.reply_text(
            _("Send me the text that you'll like to write into your PDF file"),
            reply_markup=reply_markup,
        )

        return WAIT_TEXT

    @staticmethod
    def ask_pdf_font(update: Update, context: CallbackContext):
        message = update.effective_message
        text = message.text
        _ = set_lang(update, context)

        if text == _(CANCEL):
            return cancel(update, context)

        context.user_data[TEXT_KEY] = text
        reply_markup = ReplyKeyboardMarkup(
            [[_(SKIP)]], resize_keyboard=True, one_time_keyboard=True
        )
        message.reply_text(
            "{desc_1}\n\n{desc_2}".format(
                desc_1=_(
                    "Send me the font that you'll like to use for the PDF file "
                    "or press {skip} to use the default font"
                ).format(skip=_(SKIP)),
                desc_2=_("See here for the list of supported fonts: {fonts}").format(
                    fonts='<a href="https://fonts.google.com/">Google Fonts</a>'
                ),
            ),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
        )

        return WAIT_FONT

    def check_text(self, update: Update, context: CallbackContext):
        message = update.effective_message
        message.reply_chat_action(ChatAction.TYPING)

        _ = set_lang(update, context)
        text = message.text

        if text == _(CANCEL):
            return cancel(update, context)

        if text == _(SKIP):
            return self._text_to_pdf(update, context)

        font_data = self.text_repository.get_font(text)
        if font_data is not None:
            return self._text_to_pdf(update, context, font_data)

        message.reply_text(_("Unknown font, please try again"))
        return WAIT_FONT

    def _text_to_pdf(
        self,
        update: Update,
        context: CallbackContext,
        font_data: FontData | None = None,
    ):
        _ = set_lang(update, context)
        message = update.effective_message

        try:
            text = self.telegram_service.get_user_data(context, TEXT_KEY)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return ConversationHandler.END

        message.reply_text(
            _("Creating your PDF file"), reply_markup=ReplyKeyboardRemove()
        )
        with self.pdf_service.create_pdf_from_text(text, font_data) as out_path:
            send_result_file(update, context, out_path, TaskType.text_to_pdf)

        return ConversationHandler.END
