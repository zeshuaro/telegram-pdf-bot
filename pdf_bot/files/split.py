import tempfile

from PyPDF2 import PdfFileMerger
from PyPDF2.pagerange import PageRange
from telegram import ReplyKeyboardRemove
from telegram.ext import ConversationHandler
from telegram.ext.dispatcher import run_async
from telegram.parsemode import ParseMode

from pdf_bot.constants import WAIT_SPLIT_RANGE, PDF_INFO
from pdf_bot.utils import open_pdf, write_send_pdf
from pdf_bot.language import set_lang
from pdf_bot.files.utils import get_back_markup, check_back_user_data


def ask_split_range(update, context):
    _ = set_lang(update, context)
    update.effective_message.reply_text(_(
        'Send me the range of pages that you\'ll like to keep. '
        'Use ⚡ *INSTANT VIEW* from below or refer to '
        '[here](http://telegra.ph/Telegram-PDF-Bot-07-16) for some range examples.'),
        parse_mode=ParseMode.MARKDOWN, reply_markup=get_back_markup(update, context))

    return WAIT_SPLIT_RANGE


@run_async
def split_pdf(update, context):
    result = check_back_user_data(update, context)
    if result is not None:
        return result

    _ = set_lang(update, context)
    message = update.effective_message
    split_range = message.text

    if not PageRange.valid(split_range):
        message.reply_text(_(
            'The range is invalid. Try again', reply_markup=get_back_markup(update, context)))

        return WAIT_SPLIT_RANGE

    message.reply_text(_('Splitting your PDF file'), reply_markup=ReplyKeyboardRemove())

    with tempfile.NamedTemporaryFile() as tf:
        # Download PDF file
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)
        pdf_reader = open_pdf(update, context, tf.name)

        if pdf_reader is not None:
            merger = PdfFileMerger()
            merger.append(pdf_reader, pages=PageRange(split_range))
            write_send_pdf(update, context, merger, file_name, 'split')

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END
