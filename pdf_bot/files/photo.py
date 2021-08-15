import os
import shutil
import tempfile

import pdf2image
from PyPDF2 import PdfFileWriter
from telegram import ChatAction, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import MAX_FILESIZE_DOWNLOAD, MAX_FILESIZE_UPLOAD
from telegram.error import BadRequest
from telegram.ext import ConversationHandler

from pdf_bot.commands import process_photo
from pdf_bot.constants import (
    BACK,
    BEAUTIFY,
    CANCEL,
    COMPRESSED,
    EXTRACT_PHOTO,
    PDF_INFO,
    PHOTOS,
    TO_PDF,
    WAIT_EXTRACT_PHOTO_TYPE,
    WAIT_PHOTO_TASK,
    WAIT_TO_PHOTO_TYPE,
)
from pdf_bot.files.utils import check_back_user_data, run_cmd
from pdf_bot.language import set_lang
from pdf_bot.stats import update_stats
from pdf_bot.utils import (
    check_user_data,
    get_support_markup,
    open_pdf,
    send_result_file,
)

PHOTO_ID = "photo_id"
MAX_MEDIA_GROUP = 10


def ask_photo_task(update, context, photo_file):
    _ = set_lang(update, context)
    message = update.effective_message

    if photo_file.file_size >= MAX_FILESIZE_DOWNLOAD:
        message.reply_text(
            "{desc_1}\n\n{desc_2}".format(
                desc_1=_("Your photo is too large for me to download"),
                desc_2=_(
                    "Note that this is a Telegram Bot limitation and there's "
                    "nothing I can do unless Telegram changes this limit"
                ),
            ),
        )

        return ConversationHandler.END

    context.user_data[PHOTO_ID] = photo_file.file_id
    keyboard = [[_(BEAUTIFY), _(TO_PDF)], [_(CANCEL)]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=True
    )
    message.reply_text(
        _("Select the task that you'll like to perform"), reply_markup=reply_markup
    )

    return WAIT_PHOTO_TASK


def process_photo_task(update, context):
    """
    Receive the task and perform the task on the photo
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating the conversation has ended
    """
    if not check_user_data(update, context, PHOTO_ID):
        return ConversationHandler.END

    _ = set_lang(update, context)
    user_data = context.user_data
    file_id = user_data[PHOTO_ID]

    if update.effective_message.text == _(BEAUTIFY):
        process_photo(update, context, [file_id], is_beautify=True)
    else:
        process_photo(update, context, [file_id], is_beautify=False)

    if user_data[PHOTO_ID] == file_id:
        del user_data[PHOTO_ID]

    return ConversationHandler.END


def get_pdf_preview(update, context):
    result = check_back_user_data(update, context)
    if result is not None:
        return result

    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Extracting a preview for your PDF file"), reply_markup=ReplyKeyboardRemove()
    )

    with tempfile.NamedTemporaryFile() as tf1:
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]
        pdf_reader = open_pdf(update, context, file_id, tf1.name)

        if pdf_reader:
            # Get first page of PDF file
            pdf_writer = PdfFileWriter()
            pdf_writer.addPage(pdf_reader.getPage(0))

            with tempfile.NamedTemporaryFile() as tf2:
                # Write cover preview PDF file
                with open(tf2.name, "wb") as f:
                    pdf_writer.write(f)

                with tempfile.TemporaryDirectory() as dir_name:
                    # Convert cover preview to JPEG
                    out_fn = os.path.join(
                        dir_name, f"Preview_{os.path.splitext(file_name)[0]}.png"
                    )
                    imgs = pdf2image.convert_from_path(tf2.name, fmt="png")
                    imgs[0].save(out_fn)

                    # Send result file
                    send_result_file(update, context, out_fn, "preview")

    # Clean up memory and files
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END


def ask_photo_results_type(update, context):
    _ = set_lang(update, context)
    if update.effective_message.text == _(EXTRACT_PHOTO):
        return_type = WAIT_EXTRACT_PHOTO_TYPE
    else:
        return_type = WAIT_TO_PHOTO_TYPE

    keyboard = [[_(PHOTOS), _(COMPRESSED)], [_(BACK)]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=True
    )
    update.effective_message.reply_text(
        _("Select the result file format"), reply_markup=reply_markup
    )

    return return_type


def pdf_to_photos(update, context):
    if not check_user_data(update, context, PDF_INFO):
        return ConversationHandler.END

    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Converting your PDF file into photos"), reply_markup=ReplyKeyboardRemove()
    )

    with tempfile.NamedTemporaryFile() as tf:
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            # Setup the directory for the photos
            dir_name = os.path.join(tmp_dir_name, "PDF_Photos")
            os.mkdir(dir_name)

            # Convert the PDF file into photos
            pdf2image.convert_from_path(
                tf.name,
                output_folder=dir_name,
                output_file=os.path.splitext(file_name)[0],
                fmt="png",
            )

            # Handle the result photos
            send_result_photos(update, context, dir_name, "to_photos")

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END


def get_pdf_photos(update, context):
    if not check_user_data(update, context, PDF_INFO):
        return ConversationHandler.END

    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Extracting all the photos in your PDF file"),
        reply_markup=ReplyKeyboardRemove(),
    )

    with tempfile.NamedTemporaryFile() as tf:
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            dir_name = os.path.join(tmp_dir_name, "Photos_In_PDF")
            os.mkdir(dir_name)
            if not write_photos_in_pdf(tf.name, dir_name, file_name):
                update.effective_message.reply_text(
                    _("Something went wrong, please try again")
                )
            else:
                if not os.listdir(dir_name):
                    update.effective_message.reply_text(
                        _("I couldn't find any photos in your PDF file")
                    )
                else:
                    send_result_photos(update, context, dir_name, "get_photos")

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END


def write_photos_in_pdf(input_fn, dir_name, file_name):
    root_file_name = os.path.splitext(file_name)[0]
    image_prefix = os.path.join(dir_name, root_file_name)
    command = f'pdfimages -png "{input_fn}" "{image_prefix}"'

    return run_cmd(command)


def send_result_photos(update, context, dir_name, task):
    _ = set_lang(update, context)
    message = update.effective_message

    if message.text == _(PHOTOS):
        for photo_name in sorted(os.listdir(dir_name)):
            photo_path = os.path.join(dir_name, photo_name)
            if os.path.getsize(photo_path) <= MAX_FILESIZE_UPLOAD:
                try:
                    message.chat.send_action(ChatAction.UPLOAD_PHOTO)
                    message.reply_photo(open(photo_path, "rb"))
                except BadRequest:
                    message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
                    message.reply_document(open(photo_path, "rb"))

        message.reply_text(
            _("See above for all your photos"),
            reply_markup=get_support_markup(update, context),
        )
        update_stats(update, task)
    else:
        # Compress the directory of photos
        shutil.make_archive(dir_name, "zip", dir_name)

        # Send result file
        send_result_file(update, context, f"{dir_name}.zip", task)
