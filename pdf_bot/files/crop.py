import os
import tempfile

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler

from pdf_bot.consts import (
    BACK,
    BY_PERCENT,
    BY_SIZE,
    PDF_INFO,
    WAIT_CROP_OFFSET,
    WAIT_CROP_PERCENT,
    WAIT_CROP_TYPE,
)
from pdf_bot.files.utils import run_cmd
from pdf_bot.language import set_lang
from pdf_bot.utils import send_result_file

MIN_PERCENT = 0
MAX_PERCENT = 100


def ask_crop_type(update, context):
    _ = set_lang(update, context)
    keyboard = [[_(BY_PERCENT), _(BY_SIZE)], [_(BACK)]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True
    )
    update.effective_message.reply_text(
        _("Select the crop type that you'll like to perform"), reply_markup=reply_markup
    )

    return WAIT_CROP_TYPE


def ask_crop_value(update, context):
    _ = set_lang(update, context)
    message = update.effective_message
    reply_markup = ReplyKeyboardMarkup(
        [[_(BACK)]], one_time_keyboard=True, resize_keyboard=True
    )

    if message.text == _(BY_PERCENT):
        message.reply_text(
            "{desc_1}\n\n{desc_2}".format(
                desc_1=_(
                    "Send me a number between {min_percent} and {max_percent}"
                ).format(min_percent=MIN_PERCENT, max_percent=MAX_PERCENT),
                desc_2=_(
                    "This is the percentage of margin space to retain "
                    "between the content in your PDF file and the page"
                ),
            ),
            reply_markup=reply_markup,
        )

        return WAIT_CROP_PERCENT

    message.reply_text(
        "{desc_1}\n\n{desc_2}".format(
            desc_1=_("Send me a number that you'll like to adjust the margin size"),
            desc_2=_(
                "Positive numbers will decrease the margin size "
                "and negative numbers will increase it"
            ),
        ),
        reply_markup=reply_markup,
    )

    return WAIT_CROP_OFFSET


def check_crop_percent(update, context):
    _ = set_lang(update, context)
    message = update.effective_message

    if message.text == _(BACK):
        return ask_crop_type(update, context)

    try:
        percent = float(message.text)
    except ValueError:
        message.reply_text(
            _(
                "The number must be between {min_percent} and {max_percent}, "
                "please try again"
            ).format(min_percent=MIN_PERCENT, max_percent=MAX_PERCENT),
        )

        return WAIT_CROP_PERCENT

    return crop_pdf(update, context, percent=percent)


def check_crop_size(update, context):
    _ = set_lang(update, context)
    message = update.effective_message

    if message.text == _(BACK):
        return ask_crop_type(update, context)

    try:
        offset = float(update.effective_message.text)
    except ValueError:
        _ = set_lang(update, context)
        update.effective_message.reply_text(
            _("The number is invalid, please try again")
        )

        return WAIT_CROP_OFFSET

    return crop_pdf(update, context, offset=offset)


def crop_pdf(update, context, percent=None, offset=None):
    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Cropping your PDF file"), reply_markup=ReplyKeyboardRemove()
    )

    with tempfile.NamedTemporaryFile(suffix=".pdf") as tf:
        user_data = context.user_data
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)

        with tempfile.TemporaryDirectory() as dir_name:
            out_fn = os.path.join(dir_name, f"Cropped_{file_name}")
            command = f'pdf-crop-margins -o "{out_fn}" "{tf.name}"'

            if percent is not None:
                command += f" -p {percent}"
            else:
                command += f" -a {offset}"

            if run_cmd(command):
                send_result_file(update, context, out_fn, "crop")
            else:
                update.effective_message.reply_text(
                    _("Something went wrong, please try again")
                )

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END
