import os
import tempfile

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async
from weasyprint import HTML

from pdf_bot.constants import CANCEL, TEXT_FILTER
from pdf_bot.utils import (
    send_result_file,
    cancel,
)
from pdf_bot.language import set_lang

WAIT_TEXT = 0
BASE_HTML = """<!DOCTYPE html>
<html>
<body>
<p>{}</p>
</body>
</html>"""


def text_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("text", ask_text, run_async=True)],
        states={WAIT_TEXT: [MessageHandler(TEXT_FILTER, text_to_pdf, run_async=True)]},
        fallbacks=[
            CommandHandler("cancel", cancel, run_async=True),
            MessageHandler(TEXT_FILTER, check_text, run_async=True),
        ],
        allow_reentry=True,
    )

    return conv_handler


def ask_text(update, context):
    _ = set_lang(update, context)
    reply_markup = ReplyKeyboardMarkup(
        [[_(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
    )
    update.effective_message.reply_text(
        _("Send me the text that you'll like to write into your PDF file"),
        reply_markup=reply_markup,
    )

    return WAIT_TEXT


def check_text(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text == _(CANCEL):
        return cancel(update, context)


def text_to_pdf(update, context):
    _ = set_lang(update, context)
    message = update.effective_message
    text = message.text

    if text == _(CANCEL):
        return cancel(update, context)

    message.reply_text(_("Creating your PDF file"), reply_markup=ReplyKeyboardRemove())
    html = HTML(string=BASE_HTML.format(text.replace("\n", "<br/>")))

    with tempfile.TemporaryDirectory() as dir_name:
        out_fn = os.path.join(dir_name, "Text.pdf")
        html.write_pdf(out_fn)
        send_result_file(update, context, out_fn, "text")

    return ConversationHandler.END
