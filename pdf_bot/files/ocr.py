import os
import tempfile

import ocrmypdf
from ocrmypdf.exceptions import PriorOcrFoundError
from telegram import ReplyKeyboardRemove
from telegram.ext import ConversationHandler

from pdf_bot.constants import PDF_INFO
from pdf_bot.language import set_lang
from pdf_bot.utils import check_user_data, send_result_file


def add_ocr_to_pdf(update, context):
    if not check_user_data(update, context, PDF_INFO):
        return ConversationHandler.END

    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Adding an OCR text layer to your PDF file"),
        reply_markup=ReplyKeyboardRemove(),
    )

    with tempfile.NamedTemporaryFile() as tf:
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)

        with tempfile.TemporaryDirectory() as dir_name:
            out_fn = os.path.join(dir_name, f"OCR_{os.path.splitext(file_name)[0]}.pdf")
            try:
                # logging.getLogger("ocrmypdf").setLevel(logging.WARNING)
                ocrmypdf.ocr(tf.name, out_fn, deskew=True, progress_bar=False)
                send_result_file(update, context, out_fn, "ocr")
            except PriorOcrFoundError:
                update.effective_message.reply_text(
                    _("Your PDF file already has a text layer")
                )

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END
