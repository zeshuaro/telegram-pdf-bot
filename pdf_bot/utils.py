import os
import tempfile

from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.utils import PdfReadError
from telegram import ChatAction
from telegram import ReplyKeyboardRemove
from telegram.constants import *
from telegram.ext import ConversationHandler
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import *


# Cancels feedback operation
@run_async
def cancel(update, _):
    update.message.reply_text('Operation cancelled.', reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


# Check PDF file
def check_pdf(update):
    pdf_status = PDF_OK
    pdf_file = update.message.document

    if not pdf_file.mime_type.endswith("pdf"):
        pdf_status = PDF_INVALID_FORMAT
        update.message.reply_text("The file you sent is not a PDF file. Please try again and send me a PDF file or "
                                  "type /cancel to cancel the operation.")
    elif pdf_file.file_size >= MAX_FILESIZE_DOWNLOAD:
        pdf_status = PDF_TOO_LARGE
        update.message.reply_text("The PDF file you sent is too large for me to download. "
                                  "Sorry that I can't process your PDF file. Operation cancelled.")

    return pdf_status


# Open PDF file, check if is is valid and encrypted
def open_pdf(filename, update, file_type=None):
    pdf_reader = None

    try:
        pdf_reader = PdfFileReader(open(filename, "rb"))
        if pdf_reader.isEncrypted:
            if file_type:
                text = f"Your {file_type} PDF file is encrypted. " \
                       f"Please decrypt it yourself or decrypt it with me first. Operation cancelled."
            else:
                text = "Your PDF file is encrypted. Please decrypt it yourself or decrypt it with me first. " \
                       "Operation cancelled."

            pdf_reader = None
            update.message.reply_text(text)
    except PdfReadError:
        text = "Your PDF file seems to be invalid and I couldn't open and read it. Operation cancelled."
        update.message.reply_text(text)

    return pdf_reader


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
        pdf_reader = open_pdf(tf.name, update)

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
            send_result(update, pdf_writer, file_name, file_type)

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]


# Send a list of filenames
@run_async
def send_file_names(update, filenames, file_type):
    text = f'You have sent me the following {file_type}:\n'
    for i, filename in enumerate(filenames):
        text += f'{i + 1}: {filename}\n'

    update.message.reply_text(text)


def send_result(update, pdf_writer, file_name, file_type, caption=None):
    """
    Send result file to user
    Args:
        update: the update object
        pdf_writer: the PdfFileWriter object
        file_name: the file name
        file_type: the file type
        caption: the caption of the message

    Returns:
        None
    """
    with tempfile.TemporaryDirectory() as dir_name:
        new_fn = f'{file_type.title()}_{file_name}'
        out_fn = os.path.join(dir_name, new_fn)

        with open(out_fn, 'wb') as f:
            pdf_writer.write(f)

        if os.path.getsize(out_fn) >= MAX_FILESIZE_UPLOAD:
            update.message.reply_text(f"The {file_type} PDF file is too large for me to send to you.")
        else:
            update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
            if caption is not None:
                update.message.reply_document(document=open(new_fn, "rb"), caption=caption)
            else:
                update.message.reply_document(document=open(new_fn, "rb"),
                                              caption=f"Here is your {file_type} PDF file.")
