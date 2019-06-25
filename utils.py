import os
import tempfile

from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.utils import PdfReadError
from telegram import ChatAction
from telegram.constants import *

from constants import *


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


# Master function for different PDF file manipulations
def work_on_pdf(bot, update, user_data, file_type, encrypt_pw=None, rotate_degree=None, scale_by=None, scale_to=None):
    prefix = f"{file_type.title()}_"
    temp_files = [tempfile.NamedTemporaryFile(), tempfile.NamedTemporaryFile(prefix=prefix, suffix=".pdf")]
    filename, out_filename = [x.name for x in temp_files]

    file_id = user_data["pdf_id"]
    pdf_file = bot.get_file(file_id)
    pdf_file.download(custom_path=filename)
    pdf_reader = open_pdf(filename, update)

    if pdf_reader:
        pdf_writer = PdfFileWriter()
        for page in pdf_reader.pages:
            if rotate_degree:
                pdf_writer.addPage(page.rotateClockwise(rotate_degree))
            elif scale_by:
                page.scale(scale_by[0], scale_by[1])
                pdf_writer.addPage(page)
            elif scale_to:
                page.scaleTo(scale_to[0], scale_to[1])
                pdf_writer.addPage(page)
            else:
                pdf_writer.addPage(page)

        if encrypt_pw:
            pdf_writer.encrypt(encrypt_pw)

        with open(out_filename, "wb") as f:
            pdf_writer.write(f)

        send_result(update, out_filename, file_type)

    if user_data["pdf_id"] == file_id:
        del user_data["pdf_id"]
    for tf in temp_files:
        tf.close()


# Send result file to user
def send_result(update, filename, file_type, caption=None):
    if os.path.getsize(filename) >= MAX_FILESIZE_UPLOAD:
        update.message.reply_text(f"The {file_type} PDF file is too large for me to send to you, sorry.")
    else:
        update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        if caption:
            update.message.reply_document(document=open(filename, "rb"),
                                          caption=caption)
        else:
            update.message.reply_document(document=open(filename, "rb"),
                                          caption=f"Here is your {file_type} PDF file.")
