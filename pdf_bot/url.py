import logging
import os
import tempfile
from urllib.parse import urlparse

from logbook import Logger
from telegram import ChatAction, Update
from telegram.ext import CallbackContext
from weasyprint import HTML
from weasyprint.urls import URLFetchingError

from pdf_bot.language import set_lang
from pdf_bot.utils import get_support_markup, send_result_file

URLS = "urls"
logging.getLogger("weasyprint").setLevel(100)


def process_url(update: Update, context: CallbackContext):
    url = update.effective_message.text
    if url.split("?")[0].endswith(".pdf"):
        download_pdf(update, context)
    else:
        url_to_pdf(update, context)


def download_pdf(update: Update, context: CallbackContext):
    _ = set_lang(update, context)
    reply_markup = get_support_markup(update, context)

    message = update.effective_message
    message.reply_chat_action(ChatAction.UPLOAD_DOCUMENT)
    message.reply_document(
        document=message.text,
        caption=_("Here is your result file"),
        reply_markup=reply_markup,
    )


def url_to_pdf(update: Update, context: CallbackContext):
    log = Logger()
    _ = set_lang(update, context)
    message = update.effective_message
    url = message.text
    user_data = context.user_data

    log.info(f"Received update {update} to convert URL to PDF")
    if user_data is not None and URLS in user_data and url in user_data[URLS]:
        message.reply_text(
            _("You've sent me this web page already and I'm still converting it")
        )
        log.info(f"Finished update {update}, URL convert still in progress")
    else:
        message.reply_text(_("Converting your web page into a PDF file"))
        if URLS in user_data:
            user_data[URLS].add(url)
        else:
            user_data[URLS] = {url}

        with tempfile.TemporaryDirectory() as dir_name:
            out_fn = os.path.join(dir_name, f"{urlparse(url).netloc}.pdf")
            try:
                HTML(url=url).write_pdf(out_fn)
                send_result_file(update, context, out_fn, "url")
            except URLFetchingError:
                message.reply_text(_("Unable to reach your web page"))

        user_data[URLS].remove(url)
        log.info(f"Finished update {update} to convert URL to PDF")
