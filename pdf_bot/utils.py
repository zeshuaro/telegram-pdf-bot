import os
import tempfile
from threading import Lock

from PyPDF2 import PdfFileReader
from PyPDF2.errors import PdfReadError
from telegram import (
    ChatAction,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import MAX_FILESIZE_UPLOAD
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import EventAction, TaskType, send_event
from pdf_bot.consts import CANCEL, CHANNEL_NAME, PAYMENT
from pdf_bot.language import set_lang


def cancel(update, context):
    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Action cancelled"), reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def reply_with_cancel_btn(update: Update, context: CallbackContext, text: str):
    _ = set_lang(update, context)
    reply_markup = ReplyKeyboardMarkup(
        [[_(CANCEL)]], resize_keyboard=True, one_time_keyboard=True
    )
    update.effective_message.reply_text(text, reply_markup=reply_markup)


def check_user_data(
    update: Update, context: CallbackContext, key: str, lock: Lock = None
) -> bool:
    """
    Check if the specified key exists in user_data
    Args:
        update: the update object
        context: the context object
        key: the string of key

    Returns:
        The boolean indicating if the key exists or not
    """
    data_ok = True
    if lock is not None:
        lock.acquire()

    if key not in context.user_data:
        data_ok = False
        _ = set_lang(update, context)
        update.effective_message.reply_text(
            _("Something went wrong, please start over again")
        )

    if lock is not None:
        lock.release()

    return data_ok


def open_pdf(update, context, file_id, file_name, task_type=None):
    """
    Download, open and validate PDF file
    Args:
        update: the update object
        context: the context object
        file_id: the string of the file ID
        file_name: the string of the file name
        file_type: the string of the file type

    Returns:
        The PdfFileReader object or None
    """
    _ = set_lang(update, context)
    pdf_file = context.bot.get_file(file_id)
    pdf_file.download(custom_path=file_name)
    pdf_reader = None

    try:
        pdf_reader = PdfFileReader(open(file_name, "rb"))
    except PdfReadError:
        update.effective_message.reply_text(
            _("Your file is invalid and I couldn't open and process it")
        )

    if pdf_reader is not None and pdf_reader.isEncrypted:
        if task_type is not None:
            if task_type == TaskType.encrypt_pdf:
                text = _("Your PDF file is already encrypted")
            else:
                text = _(
                    "Your PDF file is encrypted and you'll have to decrypt it first"
                )
        else:
            text = _("Your PDF file is encrypted and you'll have to decrypt it first")

        pdf_reader = None
        update.effective_message.reply_text(text)

    return pdf_reader


def send_file_names(update, context, file_names, file_type):
    """
    Send a list of file names to user
    Args:
        update: the update object
        context: the context object
        file_names: the list of file names
        file_type: the string of file type

    Returns:
        None
    """
    _ = set_lang(update, context)
    text = "{desc}\n".format(
        desc=_("You've sent me these {file_type} so far:").format(file_type=file_type)
    )
    for i, filename in enumerate(file_names):
        text += f"{i + 1}: {filename}\n"

    update.effective_message.reply_text(text)


def write_send_pdf(update, context, pdf_writer, file_name, task_type: TaskType):
    with tempfile.TemporaryDirectory() as dir_name:
        new_fn = f"{task_type.value.title()}_{file_name}"
        out_fn = os.path.join(dir_name, new_fn)

        with open(out_fn, "wb") as f:
            pdf_writer.write(f)

        send_result_file(update, context, out_fn, task_type)


def send_result_file(
    update: Update, context: CallbackContext, output_filename: str, task: TaskType
):
    _ = set_lang(update, context)
    message = update.effective_message
    reply_markup = get_support_markup(update, context)

    if os.path.getsize(output_filename) >= MAX_FILESIZE_UPLOAD:
        message.reply_text(
            "{desc_1}\n\n{desc_2}".format(
                desc_1=_("The result file is too large for me to send to you"),
                desc_2=_(
                    "Note that this is a Telegram Bot limitation and there's "
                    "nothing I can do unless Telegram changes this limit"
                ),
            ),
            reply_markup=reply_markup,
        )
    else:
        if output_filename.endswith(".png"):
            message.chat.send_action(ChatAction.UPLOAD_PHOTO)
            message.reply_photo(
                open(output_filename, "rb"),
                caption=_("Here is your result file"),
                reply_markup=reply_markup,
            )
        else:
            message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
            message.reply_document(
                document=open(output_filename, "rb"),
                caption=_("Here is your result file"),
                reply_markup=reply_markup,
            )

    send_event(update, context, task, EventAction.complete)


def get_support_markup(update, context):
    """
    Create the reply markup
    Returns:
        The reply markup object
    """
    _ = set_lang(update, context)
    keyboard = [
        [
            InlineKeyboardButton(_("Join Channel"), f"https://t.me/{CHANNEL_NAME}"),
            InlineKeyboardButton(_("Support PDF Bot"), callback_data=PAYMENT),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    return reply_markup
