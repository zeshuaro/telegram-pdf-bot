import os
import tempfile
from typing import List, Tuple

import requests
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.chataction import ChatAction
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
)
from telegram.parsemode import ParseMode
from weasyprint import CSS, HTML
from weasyprint.fonts import FontConfiguration

from pdf_bot.consts import CANCEL, TEXT_FILTER
from pdf_bot.language import set_lang
from pdf_bot.utils import cancel, check_user_data, send_result_file

load_dotenv()
GOOGLE_FONTS_API_KEY = os.environ.get("GOOGLE_FONTS_API_KEY")

WAIT_TEXT = 0
WAIT_FONT = 1

TEXT = "text"
SKIP = "Skip"
DEFAULT_FONT = "Arial"


def text_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("text", ask_text)],
        states={
            WAIT_TEXT: [MessageHandler(TEXT_FILTER, ask_font)],
            WAIT_FONT: [MessageHandler(TEXT_FILTER, check_text)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
        ],
        allow_reentry=True,
    )

    return conv_handler


def ask_text(update: Update, context: CallbackContext):
    message = update.effective_message
    message.reply_chat_action(ChatAction.TYPING)

    _ = set_lang(update, context)
    reply_markup = ReplyKeyboardMarkup(
        [[_(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
    )
    message.reply_text(
        _("Send me the text that you'll like to write into your PDF file"),
        reply_markup=reply_markup,
    )

    return WAIT_TEXT


def ask_font(update: Update, context: CallbackContext):
    message = update.effective_message
    message.reply_chat_action(ChatAction.TYPING)

    _ = set_lang(update, context)
    text = message.text

    if text == _(CANCEL):
        return cancel(update, context)

    context.user_data[TEXT] = text
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


def check_text(update: Update, context: CallbackContext):
    message = update.effective_message
    message.reply_chat_action(ChatAction.TYPING)

    _ = set_lang(update, context)
    text = message.text

    if text == _(CANCEL):
        return cancel(update, context)

    font_family: str = None
    font_url: str = None

    if text == _(SKIP):
        font_family = DEFAULT_FONT
    else:
        font_family, font_url = get_font(text)

    if font_family is not None:
        return text_to_pdf(update, context, font_family, font_url)

    message.reply_text(_("Unknown font, please try again"))
    return WAIT_FONT


def get_font(font: str) -> Tuple[str, str]:
    font_family: str = None
    font_url: str = None

    r = requests.get(
        f"https://www.googleapis.com/webfonts/v1/webfonts?key={GOOGLE_FONTS_API_KEY}"
    )
    if r.status_code == 200:
        font = font.lower()
        for item in r.json()["items"]:
            if item["family"].lower() == font:
                if "regular" in item["files"]:
                    font_family = item["family"]
                    font_url = item["files"]["regular"]
                break

    return font_family, font_url


def text_to_pdf(
    update: Update, context: CallbackContext, font_family: str, font_url: str
):
    if not check_user_data(update, context, TEXT):
        return ConversationHandler.END

    _ = set_lang(update, context)
    text = context.user_data[TEXT]
    update.effective_message.reply_text(
        _("Creating your PDF file"), reply_markup=ReplyKeyboardRemove()
    )

    html = HTML(string="<p>{content}</p>".format(content=text.replace("\n", "<br/>")))
    font_config = FontConfiguration()
    stylesheets: List[CSS] = None

    if font_family != DEFAULT_FONT:
        stylesheets = [
            CSS(
                string=(
                    "@font-face {"
                    f"font-family: {font_family};"
                    f"src: url({font_url});"
                    "}"
                    "p {"
                    f"font-family: {font_family};"
                    "}"
                ),
                font_config=font_config,
            )
        ]

    with tempfile.TemporaryDirectory() as dir_name:
        out_fn = os.path.join(dir_name, "Text.pdf")
        html.write_pdf(out_fn, stylesheets=stylesheets, font_config=font_config)
        send_result_file(update, context, out_fn, "text")

    return ConversationHandler.END
