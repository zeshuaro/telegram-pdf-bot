from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import WAIT_ROTATE_DEGREE, PDF_INFO, ROTATE_90, ROTATE_180, ROTATE_270
from pdf_bot.utils import process_pdf, check_user_data


@run_async
def ask_rotate_degree(update, _):
    """
    Ask and wait for the rotation degree
    Args:
        update: the update object
        _: unused variable

    Returns:
        The variable indicating to wait for the rotation degree
    """
    keyboard = [[ROTATE_90], [ROTATE_180], [ROTATE_270]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    update.effective_message.reply_text('Select the degrees that you\'ll like to rotate your PDF file in clockwise.',
                                        reply_markup=reply_markup)

    return WAIT_ROTATE_DEGREE


@run_async
def rotate_pdf(update, context):
    """
    Rotate the PDF file with the given rotation degree
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating the conversation has ended
    """
    if not check_user_data(update, PDF_INFO, context.user_data):
        return ConversationHandler.END

    degree = int(update.effective_message.text)
    update.effective_message.reply_text(f'Rotating your PDF file clockwise by {degree} degrees',
                                        reply_markup=ReplyKeyboardRemove())
    process_pdf(update, context, 'rotated', rotate_degree=degree)

    return ConversationHandler.END
