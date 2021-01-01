import logging
import os
import tempfile

from urllib.parse import urlparse
from weasyprint import HTML
from weasyprint.urls import URLFetchingError

from pdf_bot.utils import send_result_file
from pdf_bot.language import set_lang

URLS = "urls"
logging.getLogger("weasyprint").setLevel(100)


def url_to_pdf(update, context):
    _ = set_lang(update, context)
    message = update.effective_message
    url = message.text
    user_data = context.user_data

    if user_data is not None and URLS in user_data and url in user_data[URLS]:
        message.reply_text(
            _("You've sent me this web page already and I'm still converting it")
        )
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
