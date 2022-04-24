from telegram import ReplyKeyboardMarkup

from pdf_bot.consts import (
    BLACK_AND_WHITE,
    CANCEL,
    COMPRESS,
    CROP,
    DECRYPT,
    ENCRYPT,
    EXTRACT_IMAGE,
    EXTRACT_TEXT,
    OCR,
    PREVIEW,
    RENAME,
    ROTATE,
    SCALE,
    SPLIT,
    TO_IMAGES,
    WAIT_DOC_TASK,
)
from pdf_bot.utils import set_lang


def ask_doc_task(update, context):
    _ = set_lang(update, context)
    keywords = sorted(
        [
            _(DECRYPT),
            _(ENCRYPT),
            _(ROTATE),
            _(SCALE),
            _(SPLIT),
            _(PREVIEW),
            _(TO_IMAGES),
            _(EXTRACT_IMAGE),
            _(RENAME),
            _(CROP),
            _(EXTRACT_TEXT),
            OCR,
            _(COMPRESS),
            _(BLACK_AND_WHITE),
        ]
    )
    keyboard_size = 3
    keyboard = [
        keywords[i : i + keyboard_size] for i in range(0, len(keywords), keyboard_size)
    ]
    keyboard.append([_(CANCEL)])

    reply_markup = ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=True
    )
    update.effective_message.reply_text(
        _("Select the task that you'll like to perform"), reply_markup=reply_markup
    )

    return WAIT_DOC_TASK
