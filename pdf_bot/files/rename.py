import os
import re
import shutil
import tempfile

from telegram import ReplyKeyboardRemove
from telegram.ext import ConversationHandler
from telegram.ext.dispatcher import run_async
from telegram.parsemode import ParseMode

from pdf_bot.constants import WAIT_FILE_NAME, PDF_INFO
from pdf_bot.utils import send_result_file, check_user_data


@run_async
def ask_pdf_new_name(update, context):
    """
    Ask and wait for the new file name
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the file name
    """
    update.effective_message.reply_text('Send me the file name that you\'ll like to rename your PDF file into.',
                                        reply_markup=ReplyKeyboardRemove())

    return WAIT_FILE_NAME


@run_async
def rename_pdf(update, context):
    """
    Rename the PDF file with the given file name
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the file name or the conversation has ended
    """
    if not check_user_data(update, context, PDF_INFO):
        return ConversationHandler.END

    message = update.effective_message
    text = re.sub(r'\.pdf$', '', message.text)
    invalid_chars = r'\/*?:\'<>|'

    if set(text) & set(invalid_chars):
        message.reply_text(
            f'File names can\'t contain any of the following characters:\n{invalid_chars}\n'
            f'Send me another file name.')

        return WAIT_FILE_NAME

    new_fn = '{}.pdf'.format(text)
    message.reply_text(f'Renaming your PDF file into *{new_fn}*', parse_mode=ParseMode.MARKDOWN)

    # Download PDF file
    user_data = context.user_data
    file_id, _ = user_data[PDF_INFO]
    tf = tempfile.NamedTemporaryFile()
    pdf_file = context.bot.get_file(file_id)
    pdf_file.download(custom_path=tf.name)

    with tempfile.TemporaryDirectory() as dir_name:
        out_fn = os.path.join(dir_name, new_fn)
        shutil.move(tf.name, out_fn)
        send_result_file(update, context, out_fn)

    # Clean up memory and files
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]
    try:
        tf.close()
    except FileNotFoundError:
        pass

    return ConversationHandler.END
