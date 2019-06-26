import tempfile

from PyPDF2 import PdfFileMerger
from PyPDF2.pagerange import PageRange
from telegram import ReplyKeyboardRemove
from telegram.ext import ConversationHandler
from telegram.ext.dispatcher import run_async

from constants import WAIT_SPLIT_RANGE, PDF_ID
from utils import open_pdf, send_result


@run_async
def ask_split_range(update, _):
    """
    Ask and wait for the split page range
    Args:
        update: the update object
        _: unused variable

    Returns:
        The variable indicating to wait for the split page range
    """
    update.message.reply_text('Please send me the range of pages that you will like to keep. You can use ⚡ *INSTANT '
                              'VIEW* from below or refer to [here](http://telegra.ph/Telegram-PDF-Bot-07-16) for '
                              'some range examples.', parse_mode='markdown', reply_markup=ReplyKeyboardRemove())

    return WAIT_SPLIT_RANGE


@run_async
def split_pdf(update, context):
    """
    Split the PDF file with the given split page range
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the split page range or the conversation has ended
    """
    user_data = context.user_data
    if PDF_ID not in user_data:
        return ConversationHandler.END

    split_range = update.message.text
    if not PageRange.valid(split_range):
        update.message.reply_text('The range is invalid. Please send me the range again.')

        return WAIT_SPLIT_RANGE

    update.message.reply_text('Splitting your PDF file')

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile(), tempfile.NamedTemporaryFile(prefix='Split_', suffix='.pdf')]
    file_name, out_file_name = [x.name for x in temp_files]

    # Download PDF file
    file_id = user_data[PDF_ID]
    pdf_file = context.bot.get_file(file_id)
    pdf_file.download(custom_path=file_name)
    pdf_reader = open_pdf(file_name, update)

    if pdf_reader is not None:
        merger = PdfFileMerger()
        merger.append(pdf_reader, pages=PageRange(split_range))
        merger.write(out_file_name)
        send_result(update, out_file_name, 'split')

    # Clean up memory and files
    if user_data[PDF_ID] == file_id:
        del user_data[PDF_ID]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END
