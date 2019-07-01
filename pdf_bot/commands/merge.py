import tempfile

from PyPDF2 import PdfFileMerger
from PyPDF2.utils import PdfReadError
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import WAIT_MERGE, PDF_INVALID_FORMAT, PDF_TOO_LARGE
from pdf_bot.utils import check_pdf, cancel, write_send_pdf, send_file_names

MERGE_IDS = 'merge_ids'
MERGE_NAMES = 'merge_names'


def merge_cov_handler():
    """
    Create the merge conversation handler object
    Returns:
        The conversation handler object
    """
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('merge', merge)],
        states={
            WAIT_MERGE: [
                MessageHandler(Filters.document, receive_doc),
                MessageHandler(Filters.regex('^Done$'), merge_pdf)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel), MessageHandler(Filters.regex('^Cancel$'), cancel)],
        allow_reentry=True
    )

    return conv_handler


@run_async
def merge(update, context):
    """
    Start the merge conversation
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for a file
    """
    # Clear previous merge info
    user_data = context.user_data
    if MERGE_IDS in user_data:
        del user_data[MERGE_IDS]
    if MERGE_NAMES in user_data:
        del user_data[MERGE_NAMES]

    update.message.reply_text('Send me the PDF file that you\'ll like to merge or /cancel this operation.\n\n'
                              'The files will be merged in the order that you send me.')

    return WAIT_MERGE


@run_async
def receive_doc(update, context):
    """
    Validate the file and wait for the next action
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for a file or the conversation has ended
    """
    user_data = context.user_data
    result = check_pdf(update)

    if result == PDF_INVALID_FORMAT:
        update.message.reply_text('The file you sent is not a PDF file. Send me the PDF file that you\'ll '
                                  'like to merge or /cancel this operation.')

        return WAIT_MERGE
    elif result == PDF_TOO_LARGE:
        text = 'The PDF file you sent is too large for me to download.\n\n'

        # Check if user has already sent through some PDF files
        if MERGE_NAMES in user_data and user_data[MERGE_NAMES]:
            text += 'You can continue merging with the files that you sent me or /cancel this operation.'
            update.message.reply_text(text)
            send_file_names(update, user_data[MERGE_NAMES], 'PDF files')

            return WAIT_MERGE
        else:
            text += 'I can\'t merge your PDF files.'
            update.message.reply_text(text)

            return ConversationHandler.END

    file_name = update.message.document.file_name
    file_id = update.message.document.file_id

    # Check if user has already sent through some PDF files
    if MERGE_IDS in user_data and user_data[MERGE_IDS]:
        user_data[MERGE_IDS].append(file_id)
        user_data[MERGE_NAMES].append(file_name)
    else:
        user_data[MERGE_IDS] = [file_id]
        user_data[MERGE_NAMES] = [file_name]

    reply_markup = ReplyKeyboardMarkup([['Done'], ['Cancel']], resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text('Send me the next PDF file that you\'ll like to merge or send Done if you have '
                              'sent me all the PDF files.', reply_markup=reply_markup)
    send_file_names(update, user_data[MERGE_NAMES], 'PDF files')

    return WAIT_MERGE


def merge_pdf(update, context):
    """
    Merge PDF files
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating the conversation has ended
    """
    user_data = context.user_data
    if MERGE_IDS not in user_data:
        return ConversationHandler.END

    update.message.reply_text('Merging your PDF files', reply_markup=ReplyKeyboardRemove())
    file_ids = user_data[MERGE_IDS]
    file_names = user_data[MERGE_NAMES]

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile() for _ in range(len(file_ids))]
    merger = PdfFileMerger()

    # Merge PDF files
    for i, file_id in enumerate(file_ids):
        file_name = temp_files[i].name
        file = context.bot.get_file(file_id)
        file.download(custom_path=file_name)

        try:
            merger.append(open(file_name, 'rb'))
        except PdfReadError:
            update.message.reply_text(f'I failed to merge your PDF files as '
                                      f'I could not open and read "{file_names[i]}". '
                                      f'Make sure that it is not encrypted.')

            return ConversationHandler.END

    # Send result file
    write_send_pdf(update, merger, 'files.pdf', 'merged')

    # Clean up memory and files
    if user_data[MERGE_IDS] == file_ids:
        del user_data[MERGE_IDS]
    if user_data[MERGE_NAMES] == file_names:
        del user_data[MERGE_NAMES]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END
