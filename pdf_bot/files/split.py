import tempfile

from PyPDF2 import PdfFileMerger
from PyPDF2.pagerange import PageRange
from telegram import ReplyKeyboardRemove
from telegram.ext import ConversationHandler
from telegram.parsemode import ParseMode

from pdf_bot.constants import WAIT_SPLIT_RANGE, PDF_INFO
from pdf_bot.utils import open_pdf, write_send_pdf
from pdf_bot.language import set_lang
from pdf_bot.files.utils import get_back_markup, check_back_user_data


def ask_split_range(update, context):
    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _(
            "Send me the range of pages that you'll like to keep\n\n"
            "<b>General usage</b>\n"
            "<code>:      all pages</code>\n"
            "<code>22     just the 23rd page</code>\n"
            "<code>0:3    the first three pages</code>\n"
            "<code>:3     the first three pages</code>\n"
            "<code>5:     from the 6th page onwards</code>\n"
            "<code>-1     last page only</code>\n"
            "<code>:-1    all pages but the last page</code>\n"
            "<code>-2     second last page only</code>\n"
            "<code>-2:    last two pages</code>\n"
            "<code>-3:-1  third and second last pages only</code>\n\n"
            "<b>Advanced usage</b>\n"
            "<code>::2    pages 0 2 4 ... to the end</code>\n"
            "<code>1:10:2 pages 1 3 5 7 9</code>\n"
            "<code>::-1   all pages in reversed order</code>\n"
            "<code>3:0:-1 pages 3 2 1 but not 0</code>\n"
            "<code>2::-1  pages 2 1 0</code>"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_markup(update, context),
    )

    return WAIT_SPLIT_RANGE


def split_pdf(update, context):
    result = check_back_user_data(update, context)
    if result is not None:
        return result

    _ = set_lang(update, context)
    message = update.effective_message
    split_range = message.text

    if not PageRange.valid(split_range):
        message.reply_text(
            _(
                "The range is invalid. Try again",
                reply_markup=get_back_markup(update, context),
            )
        )

        return WAIT_SPLIT_RANGE

    message.reply_text(_("Splitting your PDF file"), reply_markup=ReplyKeyboardRemove())

    with tempfile.NamedTemporaryFile() as tf:
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]
        pdf_reader = open_pdf(update, context, file_id, tf.name)

        if pdf_reader is not None:
            merger = PdfFileMerger()
            merger.append(pdf_reader, pages=PageRange(split_range))
            write_send_pdf(update, context, merger, file_name, "split")

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END
