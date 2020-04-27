import tempfile

from PyPDF2 import PdfFileMerger
from PyPDF2.utils import PdfReadError
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, ParseMode
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import (
    PDF_INVALID_FORMAT,
    PDF_TOO_LARGE,
    CANCEL,
    DONE,
    REMOVE_LAST,
)
from pdf_bot.utils import (
    check_pdf,
    cancel_with_async,
    write_send_pdf,
    send_file_names,
    check_user_data,
    cancel_without_async,
)
from pdf_bot.language import set_lang

WAIT_MERGE = 0
MERGE_IDS = "merge_ids"
MERGE_NAMES = "merge_names"


def merge_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("merge", merge)],
        states={
            WAIT_MERGE: [
                MessageHandler(Filters.document, check_doc),
                MessageHandler(Filters.text, check_text),
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_with_async)],
        allow_reentry=True,
    )

    return conv_handler


@run_async
def merge(update, context):
    context.user_data[MERGE_IDS] = []
    context.user_data[MERGE_NAMES] = []

    return ask_first_doc(update, context)


def ask_first_doc(update, context):
    _ = set_lang(update, context)
    reply_markup = ReplyKeyboardMarkup(
        [[_(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
    )
    update.effective_message.reply_text(
        _(
            "Send me the first PDF file that you'll like to merge\n\n"
            "Note that the files will be merged in the order that you send me"
        ),
        reply_markup=reply_markup,
    )

    return WAIT_MERGE


@run_async
def check_doc(update, context):
    result = check_pdf(update, context, send_msg=False)
    if result in [PDF_INVALID_FORMAT, PDF_TOO_LARGE]:
        return process_invalid_pdf(update, context, result)

    context.user_data[MERGE_IDS].append(update.effective_message.document.file_id)
    context.user_data[MERGE_NAMES].append(update.effective_message.document.file_name)

    return ask_next_doc(update, context)


def process_invalid_pdf(update, context, result):
    _ = set_lang(update, context)
    if result == PDF_INVALID_FORMAT:
        text = _("The file you've sent is not a PDF file")
    else:
        text = _("The PDF file you've sent is too large for me to download")

    update.effective_message.reply_text(text)
    if not context.user_data[MERGE_NAMES]:
        return ask_first_doc(update, context)
    else:
        return ask_next_doc(update, context)


def ask_next_doc(update, context):
    _ = set_lang(update, context)
    reply_markup = ReplyKeyboardMarkup(
        [[_(DONE)], [_(REMOVE_LAST), _(CANCEL)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    update.effective_message.reply_text(
        _(
            "Send me the next PDF file that you'll like to merge or press *Done* if you've "
            "sent me all the PDF files"
        ),
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN,
    )
    send_file_names(update, context, context.user_data[MERGE_NAMES], _("PDF files"))

    return WAIT_MERGE


@run_async
def check_text(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text == _(REMOVE_LAST):
        return remove_doc(update, context)
    elif text == _(DONE):
        return preprocess_merge_pdf(update, context)
    elif text == _(CANCEL):
        return cancel_without_async(update, context)


def remove_doc(update, context):
    if not check_user_data(update, context, MERGE_IDS):
        return ConversationHandler.END

    _ = set_lang(update, context)
    file_ids = context.user_data[MERGE_IDS]
    file_names = context.user_data[MERGE_NAMES]
    file_ids.pop()
    file_name = file_names.pop()

    update.effective_message.reply_text(
        _("*{}* has been removed for merging").format(file_name),
        parse_mode=ParseMode.MARKDOWN,
    )

    if len(file_ids) == 0:
        return ask_first_doc(update, context)
    else:
        return ask_next_doc(update, context)


def preprocess_merge_pdf(update, context):
    if not check_user_data(update, context, MERGE_IDS):
        return ConversationHandler.END

    _ = set_lang(update, context)
    num_files = len(context.user_data[MERGE_IDS])

    if num_files == 0:
        update.effective_message.reply_text(_("You haven't sent me any PDF files"))

        return ask_first_doc(update, context)
    elif num_files == 1:
        update.effective_message.reply_text(_("You've only sent me one PDF file."))

        return ask_next_doc(update, context)
    else:
        return merge_pdf(update, context)


def merge_pdf(update, context):
    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Merging your PDF files"), reply_markup=ReplyKeyboardRemove()
    )

    # Setup temporary files
    user_data = context.user_data
    file_ids = user_data[MERGE_IDS]
    file_names = user_data[MERGE_NAMES]
    temp_files = [tempfile.NamedTemporaryFile() for _ in range(len(file_ids))]
    merger = PdfFileMerger()

    # Merge PDF files
    for i, file_id in enumerate(file_ids):
        file_name = temp_files[i].name
        file = context.bot.get_file(file_id)
        file.download(custom_path=file_name)

        try:
            merger.append(open(file_name, "rb"))
        except PdfReadError:
            update.effective_message.reply_text(
                _(
                    "I can't merge your PDF files as I couldn't open and read \"{}\". "
                    "Ensure that it is not encrypted"
                ).format(file_names[i])
            )

            return ConversationHandler.END

    # Send result file
    write_send_pdf(update, context, merger, "files.pdf", "merged")

    # Clean up memory and files
    if user_data[MERGE_IDS] == file_ids:
        del user_data[MERGE_IDS]
    if user_data[MERGE_NAMES] == file_names:
        del user_data[MERGE_NAMES]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END
