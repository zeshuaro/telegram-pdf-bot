import os
import tempfile

import img2pdf
import pdf2image
from telegram import ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler, Updater

from pdf_bot.analytics import TaskType
from pdf_bot.consts import PDF_INFO
from pdf_bot.language import set_lang
from pdf_bot.utils import check_user_data, send_result_file


def black_and_white_pdf(update: Updater, context: CallbackContext):
    if not check_user_data(update, context, PDF_INFO):
        return ConversationHandler.END

    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Converting your PDF file to black and white"),
        reply_markup=ReplyKeyboardRemove(),
    )

    with tempfile.NamedTemporaryFile() as tf, tempfile.TemporaryDirectory() as dir_name:
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)

        images = pdf2image.convert_from_path(
            tf.name,
            output_folder=dir_name,
            output_file=os.path.splitext(file_name)[0],
            fmt="png",
            grayscale=True,
            paths_only=True,
        )

        out_fn = os.path.join(dir_name, f"BW_{os.path.splitext(file_name)[0]}.pdf")
        with open(out_fn, "wb") as f:
            f.write(img2pdf.convert(images))

        send_result_file(update, context, out_fn, TaskType.black_and_wite_pdf)

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END
