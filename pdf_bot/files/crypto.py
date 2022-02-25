import tempfile

from PyPDF2 import PdfFileReader, PdfFileWriter
from PyPDF2.utils import PdfReadError
from telegram import ReplyKeyboardRemove
from telegram.ext import ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import PDF_INFO, WAIT_DECRYPT_PW, WAIT_ENCRYPT_PW
from pdf_bot.files.utils import check_back_user_data, get_back_markup
from pdf_bot.language import set_lang
from pdf_bot.utils import process_pdf, write_send_pdf


def ask_decrypt_pw(update, context):
    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Send me the password to decrypt your PDF file"),
        reply_markup=get_back_markup(update, context),
    )

    return WAIT_DECRYPT_PW


def decrypt_pdf(update, context):
    result = check_back_user_data(update, context)
    if result is not None:
        return result

    _ = set_lang(update, context)
    message = update.effective_message
    message.reply_text(
        _("Decrypting your PDF file"), reply_markup=ReplyKeyboardRemove()
    )

    with tempfile.NamedTemporaryFile() as tf:
        # Download file
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)
        pdf_reader = None

        try:
            pdf_reader = PdfFileReader(open(tf.name, "rb"))
        except PdfReadError:
            message.reply_text(
                _("Your PDF file is invalid and I couldn't open and process it")
            )

        if pdf_reader is not None:
            if not pdf_reader.isEncrypted:
                message.reply_text(_("Your PDF file is not encrypted"))
            else:
                try:
                    if pdf_reader.decrypt(message.text) == 0:
                        message.reply_text(
                            _("The decryption password is incorrect, please try again")
                        )

                        return WAIT_DECRYPT_PW

                    pdf_writer = PdfFileWriter()
                    for page in pdf_reader.pages:
                        pdf_writer.addPage(page)

                    write_send_pdf(
                        update,
                        context,
                        pdf_writer,
                        file_name,
                        TaskType.decrypt_pdf,
                    )
                except NotImplementedError:
                    message.reply_text(
                        _(
                            "Your PDF file is encrypted with a method "
                            "that I can't decrypt"
                        )
                    )

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END


def ask_encrypt_pw(update, context):
    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Send me the password to encrypt your PDF file"),
        reply_markup=get_back_markup(update, context),
    )

    return WAIT_ENCRYPT_PW


def encrypt_pdf(update, context):
    result = check_back_user_data(update, context)
    if result is not None:
        return result

    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Encrypting your PDF file"), reply_markup=ReplyKeyboardRemove()
    )
    process_pdf(
        update, context, TaskType.encrypt_pdf, encrypt_pw=update.effective_message.text
    )

    return ConversationHandler.END
