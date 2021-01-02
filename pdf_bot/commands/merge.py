import tempfile

from collections import defaultdict
from PyPDF2 import PdfFileMerger
from PyPDF2.utils import PdfReadError
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, ParseMode, Update
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)
from threading import Lock


from pdf_bot.constants import (
    PDF_INVALID_FORMAT,
    PDF_TOO_LARGE,
    CANCEL,
    DONE,
    REMOVE_LAST,
    TEXT_FILTER,
)
from pdf_bot.utils import (
    check_pdf,
    write_send_pdf,
    send_file_names,
    check_user_data,
    cancel,
)
from pdf_bot.language import set_lang

WAIT_MERGE = 0
MERGE_IDS = "merge_ids"
MERGE_NAMES = "merge_names"

merge_locks = defaultdict(Lock)


def merge_cov_handler() -> ConversationHandler:
    handlers = [
        MessageHandler(Filters.document, check_doc, run_async=True),
        MessageHandler(TEXT_FILTER, check_text, run_async=True),
    ]
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("merge", merge, run_async=True)],
        states={
            WAIT_MERGE: handlers,
            ConversationHandler.WAITING: handlers,
        },
        fallbacks=[CommandHandler("cancel", cancel, run_async=True)],
        allow_reentry=True,
    )

    return conv_handler


def merge(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_message.from_user.id
    merge_locks[user_id].acquire()
    context.user_data[MERGE_IDS] = []
    context.user_data[MERGE_NAMES] = []
    merge_locks[user_id].release()

    return ask_first_doc(update, context)


def ask_first_doc(update: Update, context: CallbackContext) -> int:
    _ = set_lang(update, context)
    reply_markup = ReplyKeyboardMarkup(
        [[_(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
    )
    update.effective_message.reply_text(
        _(
            "Send me the PDF files that you'll like to merge\n\n"
            "Note that the files will be merged in the order that you send me"
        ),
        reply_markup=reply_markup,
    )

    return WAIT_MERGE


def check_doc(update: Update, context: CallbackContext) -> int:
    result = check_pdf(update, context, send_msg=False)
    if result in [PDF_INVALID_FORMAT, PDF_TOO_LARGE]:
        return process_invalid_pdf(update, context, result)

    message = update.effective_message
    user_id = message.from_user.id
    merge_locks[user_id].acquire()
    context.user_data[MERGE_IDS].append(message.document.file_id)
    context.user_data[MERGE_NAMES].append(message.document.file_name)
    result = ask_next_doc(update, context)
    merge_locks[user_id].release()

    return result


def process_invalid_pdf(
    update: Update, context: CallbackContext, pdf_result: int
) -> int:
    _ = set_lang(update, context)
    if pdf_result == PDF_INVALID_FORMAT:
        text = _("The file you've sent is not a PDF file")
    else:
        text = _("The PDF file you've sent is too large for me to download")

    update.effective_message.reply_text(text)
    user_id = update.effective_message.from_user.id
    merge_locks[user_id].acquire()

    if not context.user_data[MERGE_NAMES]:
        result = ask_first_doc(update, context)
    else:
        result = ask_next_doc(update, context)

    merge_locks[user_id].release()

    return result


def ask_next_doc(update: Update, context: CallbackContext) -> int:
    _ = set_lang(update, context)
    send_file_names(update, context, context.user_data[MERGE_NAMES], _("PDF files"))
    reply_markup = ReplyKeyboardMarkup(
        [[_(DONE)], [_(REMOVE_LAST), _(CANCEL)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    update.effective_message.reply_text(
        _(
            "Press *Done* if you've sent me all the PDF files that "
            "you'll like to merge or keep sending me the PDF files"
        ),
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN,
    )

    return WAIT_MERGE


def check_text(update: Update, context: CallbackContext) -> int:
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(REMOVE_LAST), _(DONE)]:
        user_id = update.effective_message.from_user.id
        lock = merge_locks[user_id]

        if not check_user_data(update, context, MERGE_IDS, lock):
            return ConversationHandler.END

        if text == _(REMOVE_LAST):
            return remove_doc(update, context, lock)
        elif text == _(DONE):
            return preprocess_merge_pdf(update, context, lock)
    elif text == _(CANCEL):
        return cancel(update, context)


def remove_doc(update: Update, context: CallbackContext, lock: Lock) -> int:
    _ = set_lang(update, context)
    lock.acquire()
    file_ids = context.user_data[MERGE_IDS]
    file_names = context.user_data[MERGE_NAMES]
    file_ids.pop()
    file_name = file_names.pop()

    update.effective_message.reply_text(
        _("*{}* has been removed for merging").format(file_name),
        parse_mode=ParseMode.MARKDOWN,
    )

    if len(file_ids) == 0:
        result = ask_first_doc(update, context)
    else:
        result = ask_next_doc(update, context)

    lock.release()

    return result


def preprocess_merge_pdf(update: Update, context: CallbackContext, lock: Lock) -> int:
    _ = set_lang(update, context)
    lock.acquire()
    num_files = len(context.user_data[MERGE_IDS])

    if num_files == 0:
        update.effective_message.reply_text(_("You haven't sent me any PDF files"))

        result = ask_first_doc(update, context)
    elif num_files == 1:
        update.effective_message.reply_text(_("You've only sent me one PDF file."))

        result = ask_next_doc(update, context)
    else:
        result = merge_pdf(update, context)

    lock.release()

    return result


def merge_pdf(update: Update, context: CallbackContext) -> int:
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
