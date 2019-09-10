from telegram import ReplyKeyboardMarkup

from pdf_bot.constants import DECRYPT, ENCRYPT, ROTATE, SCALE, SPLIT, PREVIEW, \
    TO_PHOTO, EXTRACT_PHOTO, RENAME, CROP, CANCEL, WAIT_DOC_TASK, EXTRACT_TEXT
from pdf_bot.utils import set_lang


def ask_doc_task(update, context):
    _ = set_lang(update, context)
    keywords = sorted([
        _(DECRYPT), _(ENCRYPT), _(ROTATE), _(SCALE), _(SPLIT), _(PREVIEW), _(TO_PHOTO),
        _(EXTRACT_PHOTO), _(RENAME), _(CROP), _(EXTRACT_TEXT)])
    keyboard_size = 3
    keyboard = [keywords[i:i + keyboard_size] for i in range(0, len(keywords), keyboard_size)]
    keyboard.append([CANCEL])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    update.effective_message.reply_text(_(
        'Select the task that you\'ll like to perform'), reply_markup=reply_markup)

    return WAIT_DOC_TASK
