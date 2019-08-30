import os
import shlex
import tempfile

from logbook import Logger
from subprocess import Popen, PIPE
from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import ConversationHandler
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import *
from pdf_bot.utils import send_result_file

MIN_PERCENT = 0
MAX_PERCENT = 100


@run_async
def ask_crop_type(update, context):
    """
    Ask and wait for the crop type
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the crop type
    """
    keyboard = [[CROP_PERCENT, CROP_SIZE], [BACK]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.effective_message.reply_text('Select the crop type that you\'ll like to perform.', reply_markup=reply_markup)

    return WAIT_CROP_TYPE


@run_async
def ask_crop_value(update, context):
    message = update.effective_message
    if message.text == CROP_PERCENT:
        message.reply_text(f'Send me a number between {MIN_PERCENT} and {MAX_PERCENT}. '
                           f'This is the percentage of margin space to retain between '
                           f'the content in your PDF file and the page.',
                           reply_markup=ReplyKeyboardRemove())

        return WAIT_CROP_PERCENT
    else:
        message.reply_text('Send me a number that you\'ll like to adjust the margin size. '
                           'Positive numbers will decrease the margin size and '
                           'negative numbers will increase it.', reply_markup=ReplyKeyboardRemove())

        return WAIT_CROP_OFFSET


@run_async
def receive_crop_percent(update, context):
    try:
        percent = float(update.effective_message.text)
    except ValueError:
        update.effective_message.reply_text(f'The number must be between {MIN_PERCENT} and {MAX_PERCENT}, try again.')

        return WAIT_CROP_PERCENT

    return crop_pdf(update, context, percent=percent)


@run_async
def receive_crop_size(update, context):
    try:
        offset = float(update.effective_message.text)
    except ValueError:
        update.effective_message.reply_text(f'The number is invalid, try again.')

        return WAIT_CROP_OFFSET

    return crop_pdf(update, context, offset=offset)


@run_async
def crop_pdf(update, context, percent=None, offset=None):
    """
    Crop the PDF file
    Args:
        update: the update object
        context: the context object
        percent: the float of percentage
        offset: the float of off set

    Returns:
        The variable indicating the conversation has ended
    """
    update.effective_message.reply_text(f'Cropping your PDF file')
    user_data = context.user_data

    with tempfile.NamedTemporaryFile(suffix='.pdf') as tf:
        file_id, file_name = user_data[PDF_INFO]
        pdf_file = context.bot.get_file(file_id)
        pdf_file.download(custom_path=tf.name)

        with tempfile.TemporaryDirectory() as dir_name:
            out_fn = os.path.join(dir_name, f'Cropped_{file_name}')
            if percent is not None:
                cmd = f'pdf-crop-margins -p {percent} -o {out_fn} {tf.name}'
            else:
                cmd = f'pdf-crop-margins -a {offset} -o {out_fn} {tf.name}'

            proc = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
            out, err = proc.communicate()

            if proc.returncode != 0:
                log = Logger()
                log.error(f'Stdout:\n{out.decode("utf-8")}\n\nStderr:\n{err.decode("utf-8")}')
                update.effective_message.reply_text('Something went wrong, try again.')
            else:
                send_result_file(update, out_fn)

    # Clean up memory
    if user_data[PDF_INFO] == file_id:
        del user_data[PDF_INFO]

    return ConversationHandler.END
