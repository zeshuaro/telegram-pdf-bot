import os
import secrets
import tempfile

from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.utils import PdfReadError
from telegram import ChatAction
from telegram import ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import MAX_FILESIZE_DOWNLOAD, MAX_FILESIZE_UPLOAD
from telegram.ext import ConversationHandler
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import PDF_OK, PDF_INVALID_FORMAT, PDF_TOO_LARGE, PDF_INFO, CHANNEL_NAME, PAYMENT


@run_async
def cancel(update, _):
    """
    Cancel operation for conversation fallback
    Args:
        update: the update object
        _:

    Returns:
        The variable indicating the conversation has ended
    """
    update.message.reply_text('Operation cancelled.', reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def check_pdf(update, send_msg=True):
    """
    Validate the PDF file
    Args:
        update: the update object
        send_msg: the bool indicating to send a message or not

    Returns:
        The variable indicating the validation result
    """
    pdf_status = PDF_OK
    pdf_file = update.message.document

    if not pdf_file.mime_type.endswith("pdf"):
        pdf_status = PDF_INVALID_FORMAT
        if send_msg:
            update.message.reply_text("The file you sent is not a PDF file. Try again and send me a PDF file or "
                                      "type /cancel to cancel the operation.")
    elif pdf_file.file_size >= MAX_FILESIZE_DOWNLOAD:
        pdf_status = PDF_TOO_LARGE
        if send_msg:
            update.message.reply_text("The PDF file you sent is too large for me to download. "
                                      "Sorry that I can't process your PDF file. Operation cancelled.")

    return pdf_status


def check_user_data(update, key, user_data):
    """
    Check if the specified key exists in user_data
    Args:
        update: the update object
        key: the string of key
        user_data: the dict of user data

    Returns:
        The boolean indicating if the key exists or not
    """
    data_ok = True
    if key not in user_data:
        data_ok = False
        update.message.reply_text('Something went wrong, start over again.')

    return data_ok


def process_pdf(update, context, file_type, encrypt_pw=None, rotate_degree=None, scale_by=None, scale_to=None):
    """
    Process different PDF file manipulations
    Args:
        update: the update object
        context: the context object
        file_type: the string of file type
        encrypt_pw: the string of encryption password
        rotate_degree: the int of rotation degree
        scale_by: the tuple of scale by values
        scale_to: the tuple of scale to values

    Returns:
        None
    """
    with tempfile.NamedTemporaryFile()as tf:
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)

        if encrypt_pw is None:
            pdf_reader = open_pdf(tf.name, update)
        else:
            pdf_reader = open_pdf(tf.name, update, file_type)

        if pdf_reader is not None:
            pdf_writer = PdfFileWriter()
            for page in pdf_reader.pages:
                if rotate_degree is not None:
                    pdf_writer.addPage(page.rotateClockwise(rotate_degree))
                elif scale_by is not None:
                    page.scale(scale_by[0], scale_by[1])
                    pdf_writer.addPage(page)
                elif scale_to is not None:
                    page.scaleTo(scale_to[0], scale_to[1])
                    pdf_writer.addPage(page)
                else:
                    pdf_writer.addPage(page)

            if encrypt_pw is not None:
                pdf_writer.encrypt(encrypt_pw)

            # Send result file
            write_send_pdf(update, pdf_writer, file_name, file_type)

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]


def open_pdf(file_name, update, file_type=None):
    """
    Open and validate PDF file
    Args:
        file_name: the string of the file name
        update: the update object
        file_type: the string of the file type

    Returns:
        The PdfFileReader object or None
    """
    pdf_reader = None
    try:
        pdf_reader = PdfFileReader(open(file_name, 'rb'))
        if pdf_reader.isEncrypted:
            if file_type:
                if file_type == 'encrypted':
                    text = 'Your PDF file is already encrypted.'
                else:
                    text = f'Your {file_type} PDF file is encrypted and you\'ll have to decrypt it first. ' \
                        f'Operation cancelled.'
            else:
                text = 'Your PDF file is encrypted and you\'ll have to decrypt it first. Operation cancelled.'

            pdf_reader = None
            update.message.reply_text(text)
    except PdfReadError:
        text = 'Your PDF file seems to be invalid and I couldn\'t open and read it. Operation cancelled.'
        update.message.reply_text(text)

    return pdf_reader


@run_async
def send_file_names(update, file_names, file_type):
    """
    Send a list of file names to user
    Args:
        update: the update object
        file_names: the list of file names
        file_type: the string of file type

    Returns:
        None
    """
    text = f'You have sent me the following {file_type}:\n'
    for i, filename in enumerate(file_names):
        text += f'{i + 1}: {filename}\n'

    update.message.reply_text(text)


def write_send_pdf(update, pdf_writer, file_name, file_type):
    """
    Write and send result PDF file to user
    Args:
        update: the update object
        pdf_writer: the PdfFileWriter object
        file_name: the file name
        file_type: the file type

    Returns:
        None
    """
    with tempfile.TemporaryDirectory() as dir_name:
        new_fn = f'{file_type.title()}_{file_name}'
        out_fn = os.path.join(dir_name, new_fn)

        with open(out_fn, 'wb') as f:
            pdf_writer.write(f)

        send_result_file(update, out_fn)


def send_result_file(update, out_fn):
    """
    Send result file to user
    Args:
        update: the update object
        out_fn: the output file name

    Returns:
        None
    """
    if secrets.randbelow(2):
        keyboard = [[InlineKeyboardButton('Join Channel', f'https://t.me/{CHANNEL_NAME}'),
                     InlineKeyboardButton('Support PDF Bot', callback_data=PAYMENT)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        reply_markup = None

    if os.path.getsize(out_fn) >= MAX_FILESIZE_UPLOAD:
        update.message.reply_text(f"The result file is too large for me to send to you.", reply_markup=reply_markup)
    else:
        update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        update.message.reply_document(document=open(out_fn, "rb"), caption=f"Here is your result file.",
                                      reply_markup=reply_markup)
