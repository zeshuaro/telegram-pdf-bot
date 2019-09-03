import tempfile

from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.utils import PdfReadError
from telegram import ReplyKeyboardRemove
from telegram.ext import ConversationHandler
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import WAIT_DECRYPT_PW, WAIT_ENCRYPT_PW, PDF_INFO
from pdf_bot.utils import write_send_pdf, process_pdf, check_user_data
from pdf_bot.language import set_lang


def ask_decrypt_pw(update, context):
    """
    Ask and wait for the decryption password
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the decryption password
    """
    _ = set_lang(update, context)
    update.effective_message.reply_text(_('Send me the password to decrypt your PDF file.'),
                                        reply_markup=ReplyKeyboardRemove())

    return WAIT_DECRYPT_PW


@run_async
def decrypt_pdf(update, context):
    """
    Decrypt the PDF file with the given password
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating the conversation has ended
    """
    if not check_user_data(update, context, PDF_INFO):
        return ConversationHandler.END

    _ = set_lang(update, context)
    message = update.effective_message
    message.reply_text(_('Decrypting your PDF file'))

    with tempfile.NamedTemporaryFile() as tf:
        # Download file
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)
        pdf_reader = None

        try:
            pdf_reader = PdfFileReader(open(tf.name, 'rb'))
        except PdfReadError:
            message.reply_text(_('I couldn\'t open and read your PDF file as it looks invalid.'))

        if pdf_reader is not None:
            if not pdf_reader.isEncrypted:
                message.reply_text(_('Your PDF file is not encrypted.'))
            else:
                try:
                    if pdf_reader.decrypt(message.text) == 0:
                        message.reply_text(_('The decryption password is incorrect, try to send it again.'))

                        return WAIT_DECRYPT_PW

                    pdf_writer = PdfFileWriter()
                    for page in pdf_reader.pages:
                        pdf_writer.addPage(page)

                    write_send_pdf(update, context, pdf_writer, file_name, 'decrypted')
                except NotImplementedError:
                    message.reply_text(_('Your PDF file is encrypted with a method that I cannot decrypt.'))

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END


def ask_encrypt_pw(update, context):
    """
    Ask and wait for the encryption password
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the encryption password
    """
    _ = set_lang(update, context)
    update.effective_message.reply_text(_('Send me the password to encrypt your PDF file.'),
                                        reply_markup=ReplyKeyboardRemove())

    return WAIT_ENCRYPT_PW


@run_async
def encrypt_pdf(update, context):
    """
    Encrypt the PDF file with the given password
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating the conversation has ended
    """
    if not check_user_data(update, context, PDF_INFO):
        return ConversationHandler.END

    _ = set_lang(update, context)
    update.effective_message.reply_text(_('Encrypting your PDF file'))
    process_pdf(update, context, 'encrypted', encrypt_pw=update.effective_message.text)

    return ConversationHandler.END
