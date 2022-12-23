from gettext import gettext as _

from telegram import Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.chataction import ChatAction
from telegram.ext import CallbackContext, ConversationHandler
from telegram.parsemode import ParseMode

from pdf_bot.analytics import TaskType
from pdf_bot.consts import CANCEL
from pdf_bot.language import LanguageService
from pdf_bot.pdf import FontData, PdfService
from pdf_bot.telegram_internal import TelegramService, TelegramServiceError
from pdf_bot.text.text_repository import TextRepository


class TextService:
    WAIT_TEXT = 0
    WAIT_FONT = 1

    TEXT_KEY = "text"
    SKIP = _("Skip")

    def __init__(
        self,
        text_repository: TextRepository,
        pdf_service: PdfService,
        telegram_service: TelegramService,
        language_service: LanguageService,
    ) -> None:
        self.text_repository = text_repository
        self.pdf_service = pdf_service
        self.telegram_service = telegram_service
        self.language_service = language_service

    def ask_pdf_text(self, update: Update, context: CallbackContext) -> int:
        _ = self.language_service.set_app_language(update, context)
        self.telegram_service.reply_with_cancel_markup(
            update,
            context,
            _("Send me the text that you'll like to write into your PDF file"),
        )
        return self.WAIT_TEXT

    def ask_pdf_font(self, update: Update, context: CallbackContext) -> int:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.effective_message  # type: ignore
        text = message.text

        if text == _(CANCEL):
            return self.telegram_service.cancel_conversation(update, context)

        context.user_data[self.TEXT_KEY] = text  # type: ignore
        reply_markup = ReplyKeyboardMarkup(
            [[_(self.SKIP)]], resize_keyboard=True, one_time_keyboard=True
        )
        message.reply_text(
            "{desc_1}\n\n{desc_2}".format(
                desc_1=_(
                    "Send me the font that you'll like to use for the PDF file "
                    "or press {skip} to use the default font"
                ).format(skip=_(self.SKIP)),
                desc_2=_("See here for the list of supported fonts: {fonts}").format(
                    fonts='<a href="https://fonts.google.com/">Google Fonts</a>'
                ),
            ),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
        )

        return self.WAIT_FONT

    def check_text(self, update: Update, context: CallbackContext) -> int:
        message: Message = update.effective_message  # type: ignore
        message.reply_chat_action(ChatAction.TYPING)

        _ = self.language_service.set_app_language(update, context)
        text = message.text

        if text == _(CANCEL):
            return self.telegram_service.cancel_conversation(update, context)

        if text == _(self.SKIP):
            return self._text_to_pdf(update, context)

        font_data = self.text_repository.get_font(text)
        if font_data is not None:
            return self._text_to_pdf(update, context, font_data)

        message.reply_text(_("Unknown font, please try again"))
        return self.WAIT_FONT

    def _text_to_pdf(
        self,
        update: Update,
        context: CallbackContext,
        font_data: FontData | None = None,
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.effective_message  # type: ignore

        try:
            text = self.telegram_service.get_user_data(context, self.TEXT_KEY)
        except TelegramServiceError as e:
            message.reply_text(_(str(e)))
            return ConversationHandler.END

        message.reply_text(
            _("Creating your PDF file"), reply_markup=ReplyKeyboardRemove()
        )
        with self.pdf_service.create_pdf_from_text(text, font_data) as out_path:
            self.telegram_service.send_file(
                update, context, out_path, TaskType.text_to_pdf
            )

        return ConversationHandler.END
