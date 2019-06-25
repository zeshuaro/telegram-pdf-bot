import tempfile

from PyPDF2 import PdfFileMerger
from PyPDF2.utils import PdfReadError
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from constants import WAIT_MERGE_FILE, PDF_INVALID_FORMAT, PDF_TOO_LARGE
from utils import check_pdf, cancel, send_result, send_file_names

MERGE_IDS = 'merge_ids'
MERGE_NAMES = 'merge_names'


def merge_cov_handler():
    """
    Create the merge conversation handler object
    Returns:
        The conversation handler object
    """
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('merge', merge, pass_user_data=True)],
        states={
            WAIT_MERGE_FILE: [MessageHandler(Filters.document, receive_file, pass_user_data=True),
                              MessageHandler(Filters.regex('^Done$'), merge_pdf, pass_user_data=True)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    return conv_handler


@run_async
def merge(update, _, user_data):
    """
    Start the merge conversation
    Args:
        update: the update object
        _: unused variable
        user_data: the dict of user data

    Returns:
        The variable indicating to wait for a file
    """
    # Clear previous merge info
    if MERGE_IDS in user_data:
        del user_data[MERGE_IDS]
    if MERGE_NAMES in user_data:
        del user_data[MERGE_NAMES]

    update.message.reply_text('Please send me the first PDF file that you will like to merge or type /cancel to '
                              'cancel this operation.\n\nThe files will be merged in the order that you send me.')

    return WAIT_MERGE_FILE


@run_async
def receive_file(update, _, user_data):
    """
    Validate the file and wait for the next action
    Args:
        update: the update object
        _: unused variable
        user_data: the dict of user data

    Returns:
        The variable indicating to wait for a file or the conversation has ended
    """
    result = check_pdf(update)
    if result == PDF_INVALID_FORMAT:
        update.message.reply_text('The file you sent is not a PDF file. Please send me the PDF file that you\'ll '
                                  'like to merge or type /cancel to cancel this operation.')

        return WAIT_MERGE_FILE
    elif result == PDF_TOO_LARGE:
        text = 'The PDF file you sent is too large for me to download.\n\n'

        # Check if user has already sent through some PDF files
        if MERGE_NAMES in user_data and user_data[MERGE_NAMES]:
            text += 'You can continue merging with the files that you sent me or type /cancel to cancel this operation.'
            update.message.reply_text(text)
            send_file_names(update, user_data[MERGE_NAMES], 'PDF files')

            return WAIT_MERGE_FILE
        else:
            text += 'Sorry that I can\'t merge your PDF files. Operation cancelled.'
            update.message.reply_text(text)

            return ConversationHandler.END

    pdf_file = update.message.document
    file_name = pdf_file.file_name
    file_id = pdf_file.file_id

    # Check if user has already sent through some PDF files
    if MERGE_IDS in user_data and user_data[MERGE_IDS]:
        user_data[MERGE_IDS].append(file_id)
        user_data[MERGE_NAMES].append(file_name)
    else:
        user_data[MERGE_IDS] = [file_id]
        user_data[MERGE_NAMES] = [file_name]

    reply_markup = ReplyKeyboardMarkup([['Done']], one_time_keyboard=True)
    update.message.reply_text('Please send me the next PDF file that you\'ll like to merge or send Done if you have '
                              'sent me all the PDF files.', reply_markup=reply_markup)
    send_file_names(update, user_data[MERGE_NAMES], 'PDF files')

    return WAIT_MERGE_FILE


def merge_pdf(update, context, user_data):
    """
    Merge PDF files
    Args:
        update: the update object
        context: the context object
        user_data: the dict of user data

    Returns:
        The variable indicating the conversation has ended
    """
    if MERGE_IDS not in user_data:
        return ConversationHandler.END

    file_ids = user_data[MERGE_IDS]
    file_names = user_data[MERGE_NAMES]
    update.message.reply_text('Merging your PDF files', reply_markup=ReplyKeyboardRemove())

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile() for _ in range(len(file_ids))]
    temp_files.append(tempfile.NamedTemporaryFile(prefix='Merged_', suffix='.pdf'))
    out_filename = temp_files[-1].name
    merger = PdfFileMerger()
    read_ok = True

    # Merge PDF files
    for i, file_id in enumerate(file_ids):
        file_name = temp_files[i].name
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=file_name)

        try:
            merger.append(open(file_name, 'rb'))
        except PdfReadError:
            read_ok = False
            update.message.reply_text(f'I could not open and read "{file_names[i]}". '
                                      f'Please make sure that it is not encrypted. Operation cancelled.')

            break

    if read_ok:
        with open(out_filename, 'wb') as f:
            merger.write(f)

        send_result(update, out_filename, 'merged')

    # Clean up memory and files
    if user_data[MERGE_IDS] == file_ids:
        del user_data[MERGE_IDS]
    if user_data[MERGE_NAMES] == file_names:
        del user_data[MERGE_NAMES]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END
