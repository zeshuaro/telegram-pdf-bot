import tempfile

from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.utils import PdfReadError
from telegram import ReplyKeyboardRemove
from telegram.ext import ConversationHandler
from telegram.ext.dispatcher import run_async

from constants import WAIT_DECRYPT_PW, WAIT_ENCRYPT_PW
from utils import send_result, work_on_pdf
from file import PDF_ID


@run_async
def ask_decrypt_pw(update, _):
    """
    Ask for the decryption password
    Args:
        update: the update object
        _: unused variable

    Returns:
        The variable indicating to wait for the decryption password
    """
    update.message.reply_text('Please send me the password to decrypt your PDF file.',
                              reply_markup=ReplyKeyboardRemove())

    return WAIT_DECRYPT_PW


@run_async
def decrypt_pdf(update, context, user_data):
    """
    Decrypt the PDF file with the given password
    Args:
        update: the update object
        context: the context object
        user_data: the dict of user data

    Returns:
        The variable indicating the conversation has ended
    """
    if PDF_ID not in user_data:
        return ConversationHandler.END

    file_id = user_data[PDF_ID]
    pw = update.message.text
    update.message.reply_text('Decrypting your PDF file')

    temp_files = [tempfile.NamedTemporaryFile(), tempfile.NamedTemporaryFile(prefix='Decrypted_', suffix='.pdf')]
    file_name, out_file_name = [x.name for x in temp_files]

    pdf_file = context.bot.get_file(file_id)
    pdf_file.download(custom_path=file_name)
    pdf_reader = None

    try:
        pdf_reader = PdfFileReader(open(file_name, 'rb'))
    except PdfReadError:
        text = 'Your PDF file seems to be invalid and I couldn\'t open and read it. Operation cancelled.'
        update.message.reply_text(text)

    if pdf_reader is not None:
        if not pdf_reader.isEncrypted:
            update.message.reply_text('Your PDF file is not encrypted. Operation cancelled.')
        else:
            try:
                if pdf_reader.decrypt(pw) == 0:
                    update.message.reply_text('The decryption password is incorrect. Please send it again.')

                    return WAIT_DECRYPT_PW
            except NotImplementedError:
                update.message.reply_text('The PDF file is encrypted with a method that I cannot decrypt. Sorry.')

                return ConversationHandler.END

            pdf_writer = PdfFileWriter()
            for page in pdf_reader.pages:
                pdf_writer.addPage(page)

            with open(out_file_name, 'wb') as f:
                pdf_writer.write(f)

            send_result(update, out_file_name, 'decrypted')

    # Clean up memory and files
    if user_data[PDF_ID] == file_id:
        del user_data[PDF_ID]
    for tf in temp_files:
        tf.close()

    return ConversationHandler.END


@run_async
def ask_encrypt_pw(update, _):
    """
    Ask for the encryption password
    Args:
        update: the update object
        _: unused variable

    Returns:
        The variable indicating to wait for the encryption password
    """
    update.message.reply_text('Please send me the password to encrypt your PDF file.',
                              reply_markup=ReplyKeyboardRemove())

    return WAIT_ENCRYPT_PW


@run_async
def encrypt_pdf(update, context, user_data):
    """
    Encrypt the PDF file with the given password
    Args:
        update: the update object
        context: the context object
        user_data: the dict of user data

    Returns:
        The variable indicating the conversation has ended
    """
    if PDF_ID not in user_data:
        return ConversationHandler.END

    update.message.reply_text('Encrypting your PDF file...')
    work_on_pdf(update, context, user_data, 'encrypted', encrypt_pw=update.message.text)

    return ConversationHandler.END