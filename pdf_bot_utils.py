from PyPDF2 import PdfFileReader
from PyPDF2.utils import PdfReadError
from telegram import ChatAction
from telegram.constants import *

from pdf_bot_globals import *


# Check PDF files
def check_pdf(update):
    update.message.chat.send_action(ChatAction.TYPING)

    pdf_status = PDF_OK
    pdf_file = update.message.document
    mime_type = pdf_file.mime_type
    file_size = pdf_file.file_size

    if not mime_type.endswith("pdf"):
        pdf_status = PDF_INVALID_FORMAT
        update.message.reply_text("The file you sent is not a PDF file. Please try again and send me a PDF file or "
                                  "type /cancel to cancel the operation.")
    elif file_size >= MAX_FILESIZE_DOWNLOAD:
        pdf_status = PDF_TOO_LARGE
        update.message.reply_text("The PDF file you sent is too large for me to download. "
                                  "Sorry that I can't process your PDF file. Operation cancelled.")

    return pdf_status


def open_pdf(filename, update, file_type=None):
    pdf_reader = None

    try:
        pdf_reader = PdfFileReader(open(filename, "rb"))
        if pdf_reader.isEncrypted:
            if file_type:
                text = f"Your {file_type}PDF file is encrypted. " \
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
