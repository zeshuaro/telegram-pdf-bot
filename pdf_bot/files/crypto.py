import tempfile

from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.utils import PdfReadError
from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import ConversationHandler
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import WAIT_DECRYPT_PW, WAIT_ENCRYPT_PW, PDF_INFO, BACK
from pdf_bot.utils import write_send_pdf, process_pdf, check_user_data
from pdf_bot.language import set_lang
from pdf_bot.files.document import ask_doc_task


def ask_decrypt_pw(update, context):
    _ = set_lang(update, context)
    reply_markup = ReplyKeyboardMarkup([[_(BACK)]], one_time_keyboard=True, resize_keyboard=True)
    update.effective_message.reply_text(_(
        'Send me the password to decrypt your PDF file'), reply_markup=reply_markup)

    return WAIT_DECRYPT_PW


@run_async
def decrypt_pdf(update, context):
    _ = set_lang(update, context)
    message = update.effective_message

    if message.text == _(BACK):
        return ask_doc_task(update, context)
    elif not check_user_data(update, context, PDF_INFO):
        return ConversationHandler.END

    message.reply_text(_('Decrypting your PDF file'), reply_markup=ReplyKeyboardRemove())

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
            message.reply_text(_(
                'Your PDF file seems to be invalid and I couldn\'t open and read it'))

        if pdf_reader is not None:
            if not pdf_reader.isEncrypted:
                message.reply_text(_('Your PDF file is not encrypted'))
            else:
                try:
                    if pdf_reader.decrypt(message.text) == 0:
                        message.reply_text(_(
                            'The decryption password is incorrect, try to send it again'))

                        return WAIT_DECRYPT_PW

                    pdf_writer = PdfFileWriter()
                    for page in pdf_reader.pages:
                        pdf_writer.addPage(page)

                    write_send_pdf(update, context, pdf_writer, file_name, 'decrypted')
                except NotImplementedError:
                    message.reply_text(_(
                        'Your PDF file is encrypted with a method that I cannot decrypt'))

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END


def ask_encrypt_pw(update, context):
    _ = set_lang(update, context)
    reply_markup = ReplyKeyboardMarkup([[_(BACK)]], one_time_keyboard=True, resize_keyboard=True)
    update.effective_message.reply_text(_(
        'Send me the password to encrypt your PDF file'), reply_markup=reply_markup)

    return WAIT_ENCRYPT_PW


@run_async
def encrypt_pdf(update, context):
    _ = set_lang(update, context)
    message = update.effective_message

    if message.text == _(BACK):
        return ask_doc_task(update, context)
    elif not check_user_data(update, context, PDF_INFO):
        return ConversationHandler.END

    message.reply_text(_('Encrypting your PDF file'), reply_markup=ReplyKeyboardRemove())
    process_pdf(update, context, 'encrypted', encrypt_pw=message.text)

    return ConversationHandler.END
