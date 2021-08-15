import os
import re
import shutil
import tempfile

from telegram import ReplyKeyboardRemove
from telegram.ext import ConversationHandler
from telegram.parsemode import ParseMode

from pdf_bot.constants import PDF_INFO, WAIT_FILE_NAME
from pdf_bot.files.utils import check_back_user_data, get_back_markup
from pdf_bot.language import set_lang
from pdf_bot.utils import send_result_file


def ask_pdf_new_name(update, context):
    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Send me the file name that you'll like to rename your PDF file into"),
        reply_markup=get_back_markup(update, context),
    )

    return WAIT_FILE_NAME


def rename_pdf(update, context):
    result = check_back_user_data(update, context)
    if result is not None:
        return result

    _ = set_lang(update, context)
    message = update.effective_message
    text = re.sub(r"\.pdf$", "", message.text)
    invalid_chars = r"\/*?:\'<>|"

    if set(text) & set(invalid_chars):
        message.reply_text(
            "{desc_1}\n{invalid_chars}\n{desc_2}".format(
                desc_1=_("File names can't contain any of the following characters:"),
                invalid_chars=invalid_chars,
                desc_2=_("Please try again"),
            ),
        )

        return WAIT_FILE_NAME

    new_fn = "{}.pdf".format(text)
    message.reply_text(
        _("Renaming your PDF file into {}").format("<b>{}</b>".format(new_fn)),
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove(),
    )

    # Download PDF file
    user_data = context.user_data
    file_id, _ = user_data[PDF_INFO]
    tf = tempfile.NamedTemporaryFile()
    pdf_file = context.bot.get_file(file_id)
    pdf_file.download(custom_path=tf.name)

    # Rename PDF file
    with tempfile.TemporaryDirectory() as dir_name:
        out_fn = os.path.join(dir_name, new_fn)
        shutil.move(tf.name, out_fn)
        send_result_file(update, context, out_fn, "rename")

    # Clean up memory and files
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]
    try:
        tf.close()
    except FileNotFoundError:
        pass

    return ConversationHandler.END
