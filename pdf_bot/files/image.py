import os
import shutil
import tempfile

import pdf2image
from PyPDF2 import PdfFileWriter
from telegram import ChatAction, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import MAX_FILESIZE_DOWNLOAD, MAX_FILESIZE_UPLOAD
from telegram.error import BadRequest
from telegram.ext import ConversationHandler

from pdf_bot.analytics import EventAction, TaskType, send_event
from pdf_bot.commands import process_image
from pdf_bot.consts import (
    BACK,
    BEAUTIFY,
    CANCEL,
    COMPRESSED,
    EXTRACT_IMAGE,
    IMAGES,
    PDF_INFO,
    TO_PDF,
    WAIT_EXTRACT_IMAGE_TYPE,
    WAIT_IMAGE_TASK,
    WAIT_TO_IMAGE_TYPE,
)
from pdf_bot.files.utils import check_back_user_data, run_cmd
from pdf_bot.language import set_lang
from pdf_bot.utils import (
    check_user_data,
    get_support_markup,
    open_pdf,
    send_result_file,
)

IMAGE_ID = "image_id"
MAX_MEDIA_GROUP = 10


def ask_image_task(update, context, image_file):
    _ = set_lang(update, context)
    message = update.effective_message

    if image_file.file_size >= MAX_FILESIZE_DOWNLOAD:
        message.reply_text(
            "{desc_1}\n\n{desc_2}".format(
                desc_1=_("Your image is too large for me to download and process"),
                desc_2=_(
                    "Note that this is a Telegram Bot limitation and there's "
                    "nothing I can do unless Telegram changes this limit"
                ),
            ),
        )

        return ConversationHandler.END

    context.user_data[IMAGE_ID] = image_file.file_id
    keyboard = [[_(BEAUTIFY), _(TO_PDF)], [_(CANCEL)]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=True
    )
    message.reply_text(
        _("Select the task that you'll like to perform"), reply_markup=reply_markup
    )

    return WAIT_IMAGE_TASK


def process_image_task(update, context):
    if not check_user_data(update, context, IMAGE_ID):
        return ConversationHandler.END

    _ = set_lang(update, context)
    user_data = context.user_data
    file_id = user_data[IMAGE_ID]

    if update.effective_message.text == _(BEAUTIFY):
        process_image(update, context, [file_id], is_beautify=True)
    else:
        process_image(update, context, [file_id], is_beautify=False)

    if user_data[IMAGE_ID] == file_id:
        del user_data[IMAGE_ID]

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
                    send_result_file(update, context, out_fn, TaskType.preview_pdf)

    # Clean up memory and files
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END


def ask_image_results_type(update, context):
    _ = set_lang(update, context)
    if update.effective_message.text == _(EXTRACT_IMAGE):
        return_type = WAIT_EXTRACT_IMAGE_TYPE
    else:
        return_type = WAIT_TO_IMAGE_TYPE

    keyboard = [[_(IMAGES), _(COMPRESSED)], [_(BACK)]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=True
    )
    update.effective_message.reply_text(
        _("Select the result file format"), reply_markup=reply_markup
    )

    return return_type


def pdf_to_images(update, context):
    if not check_user_data(update, context, PDF_INFO):
        return ConversationHandler.END

    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Converting your PDF file into images"), reply_markup=ReplyKeyboardRemove()
    )

    with tempfile.NamedTemporaryFile() as tf:
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            # Setup the directory for the images
            dir_name = os.path.join(tmp_dir_name, "PDF_Images")
            os.mkdir(dir_name)

            # Convert the PDF file into images
            pdf2image.convert_from_path(
                tf.name,
                output_folder=dir_name,
                output_file=os.path.splitext(file_name)[0],
                fmt="png",
            )

            # Handle the result images
            send_result_images(update, context, dir_name, TaskType.pdf_to_image)

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END


def get_pdf_images(update, context):
    if not check_user_data(update, context, PDF_INFO):
        return ConversationHandler.END

    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Extracting all the images in your PDF file"),
        reply_markup=ReplyKeyboardRemove(),
    )

    with tempfile.NamedTemporaryFile() as tf:
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            dir_name = os.path.join(tmp_dir_name, "Images_In_PDF")
            os.mkdir(dir_name)
            if not write_images_in_pdf(tf.name, dir_name, file_name):
                update.effective_message.reply_text(
                    _("Something went wrong, please try again")
                )
            else:
                if not os.listdir(dir_name):
                    update.effective_message.reply_text(
                        _("I couldn't find any images in your PDF file")
                    )
                else:
                    send_result_images(
                        update, context, dir_name, TaskType.get_pdf_image
                    )

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END


def write_images_in_pdf(input_fn, dir_name, file_name):
    root_file_name = os.path.splitext(file_name)[0]
    image_prefix = os.path.join(dir_name, root_file_name)
    command = f'pdfimages -png "{input_fn}" "{image_prefix}"'

    return run_cmd(command)


def send_result_images(update, context, dir_name, task: TaskType):
    _ = set_lang(update, context)
    message = update.effective_message

    if message.text == _(IMAGES):
        for image_name in sorted(os.listdir(dir_name)):
            image_path = os.path.join(dir_name, image_name)
            if os.path.getsize(image_path) <= MAX_FILESIZE_UPLOAD:
                try:
                    message.chat.send_action(ChatAction.UPLOAD_PHOTO)
                    message.reply_photo(open(image_path, "rb"))
                except BadRequest:
                    message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
                    message.reply_document(open(image_path, "rb"))

        message.reply_text(
            _("See above for all your images"),
            reply_markup=get_support_markup(update, context),
        )
        send_event(update, context, task, EventAction.complete)
    else:
        shutil.make_archive(dir_name, "zip", dir_name)
        send_result_file(update, context, f"{dir_name}.zip", task)
