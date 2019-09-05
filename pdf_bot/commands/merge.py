import tempfile

from PyPDF2 import PdfFileMerger
from PyPDF2.utils import PdfReadError
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, ParseMode
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import PDF_INVALID_FORMAT, PDF_TOO_LARGE, CANCEL, DONE
from pdf_bot.utils import check_pdf, cancel, write_send_pdf, send_file_names, check_user_data
from pdf_bot.language import set_lang

WAIT_MERGE = 0
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
                MessageHandler(Filters.text, check_text)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
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

    _ = set_lang(update, context)
    update.effective_message.reply_text(_(
        'Send me the PDF file that you\'ll like to merge or /cancel this operation\n\n'
        'The files will be merged in the order that you send me'))

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
    result = check_pdf(update, context, send_msg=False)
    message = update.effective_message

    _ = set_lang(update, context)
    if result == PDF_INVALID_FORMAT:
        message.reply_text(_(
            'The file you sent is not a PDF file. '
            'Send me the PDF file that you\'ll like to merge or /cancel this operation'))

        return WAIT_MERGE
    elif result == PDF_TOO_LARGE:
        text = _('The PDF file you sent is too large for me to download\n\n')

        # Check if user has already sent through some PDF files
        if MERGE_NAMES in user_data and user_data[MERGE_NAMES]:
            text += _('You can continue merging with the files that you sent me or '
                      '/cancel this operation')
            message.reply_text(text)
            send_file_names(update, context, user_data[MERGE_NAMES], _('PDF files'))

            return WAIT_MERGE
        else:
            text += _('I can\'t merge your PDF files')
            message.reply_text(text)

            return ConversationHandler.END

    file_id = message.document.file_id
    file_name = message.document.file_name

    # Check if user has already sent through some PDF files
    if MERGE_IDS in user_data and user_data[MERGE_IDS]:
        user_data[MERGE_IDS].append(file_id)
        user_data[MERGE_NAMES].append(file_name)
    else:
        user_data[MERGE_IDS] = [file_id]
        user_data[MERGE_NAMES] = [file_name]

    reply_markup = ReplyKeyboardMarkup([[_(DONE)], [_(CANCEL)]], resize_keyboard=True,
                                       one_time_keyboard=True)
    message.reply_text(_(
        'Send me the next PDF file that you\'ll like to merge or send *Done* if you have '
        'sent me all the PDF files'), reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    send_file_names(update, context, user_data[MERGE_NAMES], _('PDF files'))

    return WAIT_MERGE


@run_async
def check_text(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text == _(DONE):
        return merge_pdf(update, context)
    elif text == _(CANCEL):
        return cancel(update, context)


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
    if not check_user_data(update, context, MERGE_IDS):
        return ConversationHandler.END

    _ = set_lang(update, context)
    update.effective_message.reply_text(_('Merging your PDF files'),
                                        reply_markup=ReplyKeyboardRemove())
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
            update.effective_message.reply_text(_(
                'I can\'t merge your PDF files as I couldn\'t open and read "{}". '
                'Ensure that it is not encrypted').format(file_names[i]))

            return ConversationHandler.END

    # Send result file
    write_send_pdf(update, context, merger, 'files.pdf', 'merged')

    # Clean up memory and files
    if user_data[MERGE_IDS] == file_ids:
        del user_data[MERGE_IDS]
    if user_data[MERGE_NAMES] == file_names:
        del user_data[MERGE_NAMES]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END
