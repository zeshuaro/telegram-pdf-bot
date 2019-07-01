import logging
import os
import tempfile

from telegram.ext.dispatcher import run_async
from urllib.parse import urlparse
from weasyprint import HTML

from pdf_bot.utils import send_result_file

URLS = 'urls'
logging.getLogger('weasyprint').setLevel(100)


@run_async
def url_to_pdf(update, context):
    url = update.message.text
    user_data = context.user_data

    if URLS in user_data and url in user_data[URLS]:
        update.message.reply_text('You\'ve sent me this web page already and I\'m still converting it')
    else:
        update.message.reply_text('Converting your web page into a PDF file')
        if URLS in user_data:
            user_data[URLS].add(url)
        else:
            user_data[URLS] = {url}

        with tempfile.TemporaryDirectory() as dir_name:
            out_fn = os.path.join(dir_name, f'{urlparse(url).netloc}.pdf')
            HTML(url=url).write_pdf(out_fn)

            send_result_file(update, out_fn)

        user_data[URLS].remove(url)
