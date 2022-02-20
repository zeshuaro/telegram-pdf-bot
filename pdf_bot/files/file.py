from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler

from pdf_bot.consts import (
    BACK,
    BEAUTIFY,
    BY_PERCENT,
    BY_SIZE,
    CANCEL,
    COMPRESS,
    COMPRESSED,
    CROP,
    DECRYPT,
    ENCRYPT,
    EXTRACT_IMAGE,
    EXTRACT_TEXT,
    IMAGES,
    OCR,
    PDF_INFO,
    PREVIEW,
    RENAME,
    ROTATE,
    SCALE,
    SPLIT,
    TEXT_FILE,
    TEXT_FILTER,
    TEXT_MESSAGE,
    TO_DIMENSIONS,
    TO_IMAGES,
    TO_PDF,
    WAIT_CROP_OFFSET,
    WAIT_CROP_PERCENT,
    WAIT_CROP_TYPE,
    WAIT_DECRYPT_PW,
    WAIT_DOC_TASK,
    WAIT_ENCRYPT_PW,
    WAIT_EXTRACT_IMAGE_TYPE,
    WAIT_FILE_NAME,
    WAIT_IMAGE_TASK,
    WAIT_ROTATE_DEGREE,
    WAIT_SCALE_DIMENSION,
    WAIT_SCALE_PERCENT,
    WAIT_SCALE_TYPE,
    WAIT_SPLIT_RANGE,
    WAIT_TEXT_TYPE,
    WAIT_TO_IMAGE_TYPE,
)
from pdf_bot.files.compress import compress_pdf
from pdf_bot.files.crop import (
    ask_crop_type,
    ask_crop_value,
    check_crop_percent,
    check_crop_size,
)
from pdf_bot.files.crypto import (
    ask_decrypt_pw,
    ask_encrypt_pw,
    decrypt_pdf,
    encrypt_pdf,
)
from pdf_bot.files.document import ask_doc_task
from pdf_bot.files.image import (
    ask_image_results_type,
    ask_image_task,
    get_pdf_images,
    get_pdf_preview,
    pdf_to_images,
    process_image_task,
)
from pdf_bot.files.ocr import add_ocr_to_pdf
from pdf_bot.files.rename import ask_pdf_new_name, rename_pdf
from pdf_bot.files.rotate import ask_rotate_degree, check_rotate_degree
from pdf_bot.files.scale import (
    ask_scale_type,
    ask_scale_value,
    check_scale_dimension,
    check_scale_percent,
)
from pdf_bot.files.split import ask_split_range, split_pdf
from pdf_bot.files.text import ask_text_type, get_pdf_text
from pdf_bot.language import set_lang
from pdf_bot.utils import cancel


def file_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(Filters.document, check_doc),
            MessageHandler(Filters.photo, check_image),
        ],
        states={
            WAIT_DOC_TASK: [MessageHandler(TEXT_FILTER, check_doc_task)],
            WAIT_IMAGE_TASK: [MessageHandler(TEXT_FILTER, check_image_task)],
            WAIT_CROP_TYPE: [MessageHandler(TEXT_FILTER, check_crop_task)],
            WAIT_CROP_PERCENT: [MessageHandler(TEXT_FILTER, check_crop_percent)],
            WAIT_CROP_OFFSET: [MessageHandler(TEXT_FILTER, check_crop_size)],
            WAIT_DECRYPT_PW: [MessageHandler(TEXT_FILTER, decrypt_pdf)],
            WAIT_ENCRYPT_PW: [MessageHandler(TEXT_FILTER, encrypt_pdf)],
            WAIT_FILE_NAME: [MessageHandler(TEXT_FILTER, rename_pdf)],
            WAIT_ROTATE_DEGREE: [MessageHandler(TEXT_FILTER, check_rotate_degree)],
            WAIT_SPLIT_RANGE: [MessageHandler(TEXT_FILTER, split_pdf)],
            WAIT_TEXT_TYPE: [MessageHandler(TEXT_FILTER, check_text_task)],
            WAIT_SCALE_TYPE: [MessageHandler(TEXT_FILTER, check_scale_task)],
            WAIT_SCALE_PERCENT: [MessageHandler(TEXT_FILTER, check_scale_percent)],
            WAIT_SCALE_DIMENSION: [MessageHandler(TEXT_FILTER, check_scale_dimension)],
            WAIT_EXTRACT_IMAGE_TYPE: [
                MessageHandler(TEXT_FILTER, check_get_images_task)
            ],
            WAIT_TO_IMAGE_TYPE: [MessageHandler(TEXT_FILTER, check_to_images_task)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    return conv_handler


def check_doc(update, context):
    doc = update.effective_message.document
    if doc.mime_type.startswith("image"):
        return ask_image_task(update, context, doc)
    if not doc.mime_type.endswith("pdf"):
        return ConversationHandler.END
    if doc.file_size >= MAX_FILESIZE_DOWNLOAD:
        _ = set_lang(update, context)
        update.effective_message.reply_text(
            "{desc_1}\n\n{desc_2}".format(
                desc_1=_("Your file is too big for me to download and process"),
                desc_2=_(
                    "Note that this is a Telegram Bot limitation and there's "
                    "nothing I can do unless Telegram changes this limit"
                ),
            ),
        )

        return ConversationHandler.END

    context.user_data[PDF_INFO] = doc.file_id, doc.file_name
    return ask_doc_task(update, context)


def check_image(update, context):
    return ask_image_task(update, context, update.effective_message.photo[-1])


def check_doc_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text == _(CROP):
        return ask_crop_type(update, context)
    if text == _(DECRYPT):
        return ask_decrypt_pw(update, context)
    if text == _(ENCRYPT):
        return ask_encrypt_pw(update, context)
    if text in [_(EXTRACT_IMAGE), _(TO_IMAGES)]:
        return ask_image_results_type(update, context)
    if text == _(PREVIEW):
        return get_pdf_preview(update, context)
    if text == _(RENAME):
        return ask_pdf_new_name(update, context)
    if text == _(ROTATE):
        return ask_rotate_degree(update, context)
    if text in [_(SCALE)]:
        return ask_scale_type(update, context)
    if text == _(SPLIT):
        return ask_split_range(update, context)
    if text == _(EXTRACT_TEXT):
        return ask_text_type(update, context)
    if text == OCR:
        return add_ocr_to_pdf(update, context)
    if text == COMPRESS:
        return compress_pdf(update, context)
    if text == _(CANCEL):
        return cancel(update, context)

    return WAIT_DOC_TASK


def check_image_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(BEAUTIFY), _(TO_PDF)]:
        return process_image_task(update, context)
    if text == _(CANCEL):
        return cancel(update, context)

    return WAIT_IMAGE_TASK


def check_crop_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(BY_PERCENT), _(BY_SIZE)]:
        return ask_crop_value(update, context)
    if text == _(BACK):
        return ask_doc_task(update, context)

    return WAIT_CROP_TYPE


def check_scale_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(BY_PERCENT), _(TO_DIMENSIONS)]:
        return ask_scale_value(update, context)
    if text == _(BACK):
        return ask_doc_task(update, context)

    return WAIT_SCALE_TYPE


def check_text_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text == _(TEXT_MESSAGE):
        return get_pdf_text(update, context, is_file=False)
    if text == _(TEXT_FILE):
        return get_pdf_text(update, context, is_file=True)
    if text == _(BACK):
        return ask_doc_task(update, context)

    return WAIT_TEXT_TYPE


def check_get_images_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(IMAGES), _(COMPRESSED)]:
        return get_pdf_images(update, context)
    if text == _(BACK):
        return ask_doc_task(update, context)

    return WAIT_EXTRACT_IMAGE_TYPE


def check_to_images_task(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(IMAGES), _(COMPRESSED)]:
        return pdf_to_images(update, context)
    if text == _(BACK):
        return ask_doc_task(update, context)

    return WAIT_TO_IMAGE_TYPE
