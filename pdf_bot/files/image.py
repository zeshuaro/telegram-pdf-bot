from telegram import ReplyKeyboardMarkup
from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext import ConversationHandler

from pdf_bot.commands import process_image
from pdf_bot.consts import BEAUTIFY, CANCEL, TO_PDF, WAIT_IMAGE_TASK
from pdf_bot.language import set_lang
from pdf_bot.utils import check_user_data

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
