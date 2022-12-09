from telegram.ext import ConversationHandler

from pdf_bot.commands import process_image
from pdf_bot.consts import BEAUTIFY, FILE_DATA
from pdf_bot.language import set_lang
from pdf_bot.utils import check_user_data

MAX_MEDIA_GROUP = 10


def process_image_task(update, context):
    if not check_user_data(update, context, FILE_DATA):
        return ConversationHandler.END

    _ = set_lang(update, context)
    user_data = context.user_data
    file_id, _file_name = user_data[FILE_DATA]

    if update.effective_message.text == _(BEAUTIFY):
        process_image(update, context, [file_id], is_beautify=True)
    else:
        process_image(update, context, [file_id], is_beautify=False)

    return ConversationHandler.END
