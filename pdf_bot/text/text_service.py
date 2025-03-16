from gettext import gettext as _
from typing import cast

from telegram import Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes, ConversationHandler

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

    async def ask_pdf_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        _ = self.language_service.set_app_language(update, context)
        await self.telegram_service.reply_with_cancel_markup(
            update,
            context,
            _("Send me the text that you'll like to write into your PDF file"),
        )
        return self.WAIT_TEXT

    async def ask_pdf_font(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        _ = self.language_service.set_app_language(update, context)
        msg = cast("Message", update.effective_message)
        text = msg.text

        if text == _(CANCEL):
            return await self.telegram_service.cancel_conversation(update, context)

        self.telegram_service.update_user_data(context, self.TEXT_KEY, text)
        reply_markup = ReplyKeyboardMarkup(
            [[_(self.SKIP)]], resize_keyboard=True, one_time_keyboard=True
        )
        await msg.reply_text(
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

    async def check_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        msg = cast("Message", update.effective_message)
        await msg.reply_chat_action(ChatAction.TYPING)

        _ = self.language_service.set_app_language(update, context)
        msg_text = cast("str", msg.text)

        if msg_text == _(CANCEL):
            return await self.telegram_service.cancel_conversation(update, context)

        if msg_text == _(self.SKIP):
            return await self._text_to_pdf(update, context)

        font_data = self.text_repository.get_font(msg_text)
        if font_data is not None:
            return await self._text_to_pdf(update, context, font_data)

        await msg.reply_text(_("Unknown font, please try again"))
        return self.WAIT_FONT

    async def _text_to_pdf(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        font_data: FontData | None = None,
    ) -> int:
        _ = self.language_service.set_app_language(update, context)
        msg = cast("Message", update.effective_message)

        try:
            text = self.telegram_service.get_user_data(context, self.TEXT_KEY)
        except TelegramServiceError as e:
            await msg.reply_text(_(str(e)))
            return ConversationHandler.END

        await msg.reply_text(_("Creating your PDF file"), reply_markup=ReplyKeyboardRemove())
        async with self.pdf_service.create_pdf_from_text(text, font_data) as out_path:
            await self.telegram_service.send_file(update, context, out_path, TaskType.text_to_pdf)

        return ConversationHandler.END
