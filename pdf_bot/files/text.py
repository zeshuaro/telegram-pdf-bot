import os
import tempfile
import textwrap

from pdfminer.high_level import extract_text_to_fp
from telegram import ParseMode, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import MAX_MESSAGE_LENGTH
from telegram.ext import ConversationHandler

from pdf_bot.constants import BACK, PDF_INFO, TEXT_FILE, TEXT_MESSAGE, WAIT_TEXT_TYPE
from pdf_bot.language import set_lang
from pdf_bot.utils import check_user_data, send_result_file


def ask_text_type(update, context):
    _ = set_lang(update, context)
    keyboard = [[_(TEXT_MESSAGE), _(TEXT_FILE)], [_(BACK)]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True
    )
    update.effective_message.reply_text(
        _("Select how you'll like me to send the text to you"),
        reply_markup=reply_markup,
    )

    return WAIT_TEXT_TYPE


def get_pdf_text(update, context, is_file):
    if not check_user_data(update, context, PDF_INFO):
        return ConversationHandler.END

    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Extracting text from your PDF file"), reply_markup=ReplyKeyboardRemove()
    )

    with tempfile.NamedTemporaryFile() as tf:
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)

        with tempfile.TemporaryDirectory() as dir_name:
            tmp_text = tempfile.TemporaryFile()
            with open(tf.name, "rb") as f:
                extract_text_to_fp(f, tmp_text)

            tmp_text.seek(0)
            pdf_texts = textwrap.wrap(tmp_text.read().decode("utf-8").strip())
            out_fn = os.path.join(dir_name, f"{os.path.splitext(file_name)[0]}.txt")
            send_pdf_text(update, context, pdf_texts, is_file, out_fn)

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END


def send_pdf_text(update, context, pdf_texts, is_file, out_fn):
    _ = set_lang(update, context)
    message = update.effective_message

    if pdf_texts:
        if is_file:
            with open(out_fn, "w") as f:
                f.write("\n".join(pdf_texts))

            send_result_file(update, context, out_fn, "get_text")
        else:
            msg_text = ""
            for pdf_text in pdf_texts:
                if len(msg_text) + len(pdf_text) + 1 > MAX_MESSAGE_LENGTH:
                    message.reply_text(msg_text.strip())
                    msg_text = ""

                msg_text += f" {pdf_text}"

            if msg_text:
                message.reply_text(msg_text.strip())

            message.reply_text(
                _("<b>See above for all the text in your PDF file</b>"),
                parse_mode=ParseMode.HTML,
            )
    else:
        message.reply_text(_("I couldn't find any text in your PDF file"))
