import tempfile

from PyPDF2 import PdfFileMerger
from PyPDF2.utils import PdfReadError
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, ParseMode
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import PDF_INVALID_FORMAT, PDF_TOO_LARGE, CANCEL, DONE
from pdf_bot.utils import check_pdf, cancel_with_async, write_send_pdf, send_file_names, \
    check_user_data, cancel_without_async
from pdf_bot.language import set_lang

WAIT_MERGE = 0
MERGE_IDS = 'merge_ids'
MERGE_NAMES = 'merge_names'


def merge_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('merge', merge)],
        states={
            WAIT_MERGE: [MessageHandler(Filters.document, check_doc), MessageHandler(Filters.text, check_text)]
        },
        fallbacks=[CommandHandler('cancel', cancel_with_async)],
        allow_reentry=True
    )

    return conv_handler


@run_async
def merge(update, context):
    # Create clean merge info
    user_data = context.user_data
    user_data[MERGE_IDS] = []
    user_data[MERGE_NAMES] = []

    _ = set_lang(update, context)
    reply_markup = ReplyKeyboardMarkup([[_(CANCEL)]], resize_keyboard=True, one_time_keyboard=True)
    update.effective_message.reply_text(_(
        'Send me the PDF file that you\'ll like to merge\n\n'
        'Note that the files will be merged in the order that you send me'), reply_markup=reply_markup)

    return WAIT_MERGE


@run_async
def check_text(update, context):
    _ = get_lang(update, context)
    text = update.effective_message.text

    if text == _(DONE):
        return merge_pdf(update, context)
    elif text == _(CANCEL):
        return cancel_without_async(update, context)


@run_async
def check_doc(update, context):
    user_data = context.user_data
    result = check_pdf(update, context, send_msg=False)
    message = update.effective_message

    _ = get_lang(update, context)
    if result in [PDF_INVALID_FORMAT, PDF_TOO_LARGE]:
        return handle_invalid_pdf(update, context)

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


def handle_invalid_pdf(update, context):
    _ = set_lang(update, context)
    message = update.effective_message
    result = check_pdf(update, context, send_msg=False)

    if result == PDF_INVALID_FORMAT:
        text = _('The file you\'ve sent is not a PDF file\n\n')
    else:
        text = _('The PDF file you\'ve sent is too large for me to download\n\n')

    # Check if user has already sent through some PDF files
    if context.user_data[MERGE_NAMES]:
        text += _('You can continue merging with the files that you\'ve sent me')
        message.reply_text(text)
        send_file_names(update, context, context.user_data[MERGE_NAMES], _('PDF files'))
    else:
        text += _('Send me the PDF file that you\'ll like to merge\n\n')
        message.reply_text(text)

    return WAIT_MERGE


def merge_pdf(update, context):
    if not check_user_data(update, context, MERGE_IDS):
        return ConversationHandler.END

    _ = set_lang(update, context)
    update.effective_message.reply_text(_('Merging your PDF files'),
                                        reply_markup=ReplyKeyboardRemove())
    user_data = context.user_data
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
