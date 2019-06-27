import os
import pdf_diff
import tempfile

from pdf_diff import NoDifferenceError
from telegram import ChatAction
from telegram.constants import MAX_FILESIZE_UPLOAD
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import WAIT_FIRST_COMPARE_FILE, WAIT_SECOND_COMPARE_FILE, PDF_INVALID_FORMAT, PDF_OK
from pdf_bot.utils import check_pdf, cancel


# Create a compare conversation handler
def compare_cov_handler():
    """
    Create a compare conversation handler object
    Returns:
        The conversation handler object
    """
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('compare', compare)],
        states={
            WAIT_FIRST_COMPARE_FILE: [MessageHandler(Filters.document, check_first_compare_file)],
            WAIT_SECOND_COMPARE_FILE: [MessageHandler(Filters.document, check_second_compare_file)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    return conv_handler


@run_async
def compare(update, _):
    """
    Start the compare conversation
    Args:
        update: the update object
        _: unused variable

    Returns:
        The variable indicating to wait for the file
    """
    update.message.reply_text('Please send me one of the PDF files that you will like to compare or type /cancel to '
                              'cancel this operation.\n\nPlease note that I can only look for text differences.')

    return WAIT_FIRST_COMPARE_FILE


@run_async
def check_first_compare_file(update, context):
    """
    Validate the file and wait for the next action
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the file or the conversation has ended
    """
    result = check_pdf(update)
    if result == PDF_INVALID_FORMAT:
        return WAIT_FIRST_COMPARE_FILE
    elif result != PDF_OK:
        return ConversationHandler.END

    context.user_data['compare_file_id'] = update.message.document.file_id
    update.message.reply_text('Please send me the other PDF file that you will like to compare.')

    return WAIT_SECOND_COMPARE_FILE


# Receive and check for the second PDF file
# If success, compare the two PDF files
@run_async
def check_second_compare_file(update, context):
    """
    Validate the file and compare the files
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the file or the conversation has ended
    """
    if 'compare_file_id' not in context.user_data:
        return ConversationHandler.END

    result = check_pdf(update)
    if result == PDF_INVALID_FORMAT:
        return WAIT_SECOND_COMPARE_FILE
    elif result != PDF_OK:
        return ConversationHandler.END

    return compare_pdf(update, context)


# Compare two PDF files
def compare_pdf(update, context):
    user_data = context.user_data
    if 'compare_file_id' not in user_data:
        return ConversationHandler.END

    first_file_id = user_data['compare_file_id']
    update.message.reply_text('Comparing your PDF files...')

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile() for _ in range(2)]
    temp_files.append(tempfile.NamedTemporaryFile(prefix='Compared_', suffix='.png'))
    first_filename, second_filename, out_filename = [x.name for x in temp_files]

    # Download PDF files
    first_pdf_file = context.bot.get_file(first_file_id)
    first_pdf_file.download(custom_path=first_filename)
    second_pdf_file = context.bot.get_file(update.message.document.file_id)
    second_pdf_file.download(custom_path=second_filename)

    # Run pdf-diff
    try:
        pdf_diff.main(files=[first_filename, second_filename], out_file=out_filename)
        if os.path.getsize(out_filename) >= MAX_FILESIZE_UPLOAD:
            update.message.reply_text('The difference result file is too large for me to send to you, sorry.')
        else:
            update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
            update.message.reply_photo(photo=open(out_filename, 'rb'),
                                       caption='Here are the differences between your PDF files.')
    except NoDifferenceError:
        update.message.reply_text('There are no differences between the two PDF files you sent me.')

    # Clean up memory and files
    if user_data['compare_file_id'] == first_file_id:
        del user_data['compare_file_id']
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END
