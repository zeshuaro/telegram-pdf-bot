import os
import tempfile

from pdf_bot.constants import CANCEL, TEXT_FILTER
from pdf_bot.language import set_lang
from pdf_bot.utils import cancel, check_user_data, send_result_file
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
)
from weasyprint import HTML

WAIT_TEXT = 0
WAIT_FONT = 1

TEXT = "text"
SKIP = "Skip"
BASE_HTML = """<!DOCTYPE html>
<html>
<body>
<p style="font-family: {font}">{text}</p>
</body>
</html>"""

FONTS = {
    "Arial": "sans-serif",
    "Helvetica": "sans-serif",
    "Verdana": "sans-serif",
    "Trebuchet MS": "sans-serif",
    "Gill Sans": "sans-serif",
    "Noto Sans": "sans-serif",
    "Avantgarde": "sans-serif",
    "Optima": "sans-serif",
    "Arial Narrow": "sans-serif",
    "Times New Roman": "serif",
    "Didot": "serif",
    "Georgia": "serif",
    "Palatino": "serif",
    "Bookman": "serif",
    "New Century Schoolbook": "serif",
    "American Typewriter": "serif",
    "Andale Mono": "monospace",
    "Courier New": "monospace",
    "Courier": "monospace",
    "FreeMono": "monospace",
    "OCR A Std": "monospace",
    "DejaVu Sans Mono": "monospace",
    "Comic Sans": "cursive",
    "Apple Chancery": "cursive",
    "Bradley Hand": "cursive",
    "Brush Script MT": "cursive",
    "Snell Roundhand": "cursive",
    "URW Chancery L": "cursive",
    "Impact": "fantasy",
    "Luminari": "fantasy",
    "Chalkduster": "fantasy",
    "Jazz LET": "fantasy",
    "Blippo": "fantasy",
    "Stencil Std": "fantasy",
    "Marker Felt": "fantasy",
    "Trattatello": "fantasy",
}
FONT_LIST = sorted(FONTS.keys())


def text_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("text", ask_text, run_async=True)],
        states={
            WAIT_TEXT: [MessageHandler(TEXT_FILTER, ask_font, run_async=True)],
            WAIT_FONT: [MessageHandler(TEXT_FILTER, check_text, run_async=True)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel, run_async=True),
            MessageHandler(TEXT_FILTER, check_text, run_async=True),
        ],
        allow_reentry=True,
    )

    return conv_handler


def ask_text(update: Update, context: CallbackContext):
    _ = set_lang(update, context)
    reply_markup = ReplyKeyboardMarkup(
        [[_(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
    )
    update.effective_message.reply_text(
        _("Send me the text that you'll like to write into your PDF file"),
        reply_markup=reply_markup,
    )

    return WAIT_TEXT


def ask_font(update: Update, context: CallbackContext):
    _ = set_lang(update, context)
    message = update.effective_message
    text = message.text

    if text == _(CANCEL):
        return cancel(update, context)

    context.user_data[TEXT] = text
    keyboard_size = 3
    keyboard = [[_(SKIP), _(CANCEL)]] + [
        FONT_LIST[i : i + keyboard_size]
        for i in range(0, len(FONT_LIST), keyboard_size)
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=True
    )
    update.effective_message.reply_text(
        "{select_text} '{skip}' {use_default}".format(
            select_text=_("Select the font or select"),
            skip=_(SKIP),
            use_default=_("to use the default font"),
        ),
        reply_markup=reply_markup,
    )

    return WAIT_FONT


def check_text(update: Update, context: CallbackContext):
    _ = set_lang(update, context)
    message = update.effective_message
    text = message.text
    font: str = None

    if text == _(SKIP):
        font = "Arial"
    elif text in FONTS:
        font = text
    elif text == _(CANCEL):
        return cancel(update, context)

    if text is not None:
        return text_to_pdf(update, context, font)
    else:
        message.reply_text(_("Unknown font, please select a font from the list"))
        return WAIT_FONT


def text_to_pdf(update: Update, context: CallbackContext, font: str):
    if not check_user_data(update, context, TEXT):
        return ConversationHandler.END

    _ = set_lang(update, context)
    text = context.user_data[TEXT]
    update.effective_message.reply_text(
        _("Creating your PDF file"), reply_markup=ReplyKeyboardRemove()
    )
    font_family = f"{font}, {FONTS[font]}"
    html = HTML(
        string=BASE_HTML.format(font=font_family, text=text.replace("\n", "<br/>"))
    )

    with tempfile.TemporaryDirectory() as dir_name:
        out_fn = os.path.join(dir_name, "Text.pdf")
        html.write_pdf(out_fn)
        send_result_file(update, context, out_fn, "text")

    return ConversationHandler.END
