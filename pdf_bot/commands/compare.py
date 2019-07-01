import os
import pdf_diff
import tempfile

from pdf_diff import NoDifferenceError
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import WAIT_COMPARE_FIRST, WAIT_COMPARE_SECOND, PDF_INVALID_FORMAT, PDF_OK
from pdf_bot.utils import check_pdf, cancel, send_result_file

COMPARE_ID = 'compare_id'


def compare_cov_handler():
    """
    Create a compare conversation handler object
    Returns:
        The conversation handler object
    """
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('compare', compare)],
        states={
            WAIT_COMPARE_FIRST: [MessageHandler(Filters.document, receive_first_doc)],
            WAIT_COMPARE_SECOND: [MessageHandler(Filters.document, receive_second_doc)],
        },
        fallbacks=[CommandHandler('cancel', cancel), MessageHandler(Filters.regex('^Cancel$'), cancel)],
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
    update.message.reply_text('Send me one of the PDF files that you\'ll like to compare or /cancel this operation.\n\n'
                              'Note that I can only look for text differences.')

    return WAIT_COMPARE_FIRST


@run_async
def receive_first_doc(update, context):
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
        return WAIT_COMPARE_FIRST
    elif result != PDF_OK:
        return ConversationHandler.END

    context.user_data[COMPARE_ID] = update.message.document.file_id
    update.message.reply_text('Send me the other PDF file that you\'ll like to compare.')

    return WAIT_COMPARE_SECOND


@run_async
def receive_second_doc(update, context):
    """
    Validate the file and compare the files
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the file or the conversation has ended
    """
    if COMPARE_ID not in context.user_data:
        return ConversationHandler.END

    result = check_pdf(update)
    if result == PDF_INVALID_FORMAT:
        return WAIT_COMPARE_SECOND
    elif result != PDF_OK:
        return ConversationHandler.END

    return compare_pdf(update, context)


def compare_pdf(update, context):
    """
    Compare two PDF files
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating the conversation has ended
    """
    user_data = context.user_data
    if COMPARE_ID not in user_data:
        return ConversationHandler.END

    update.message.reply_text('Comparing your PDF files')

    # Setup temporary files
    temp_files = [tempfile.NamedTemporaryFile() for _ in range(2)]
    first_fn, second_fn = [x.name for x in temp_files]

    # Download PDF files
    first_file_id = user_data[COMPARE_ID]
    first_file = context.bot.get_file(first_file_id)
    first_file.download(custom_path=first_fn)
    second_file = context.bot.get_file(update.message.document.file_id)
    second_file.download(custom_path=second_fn)

    try:
        with tempfile.TemporaryDirectory() as dir_name:
            out_fn = os.path.join(dir_name, 'Differences.png')

            # Run pdf-diff
            pdf_diff.main(files=[first_fn, second_fn], out_file=out_fn)

            # Send result file
            send_result_file(update, out_fn)
    except NoDifferenceError:
        update.message.reply_text('There are no differences between your PDF files.')

    # Clean up memory and files
    if user_data[COMPARE_ID] == first_file_id:
        del user_data[COMPARE_ID]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END
