from telegram import ReplyKeyboardRemove
from telegram.ext import ConversationHandler
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import WAIT_SCALE_BY_X, WAIT_SCALE_BY_Y, WAIT_SCALE_TO_X, WAIT_SCALE_TO_Y, PDF_INFO, SCALE_BY
from pdf_bot.utils import process_pdf, check_user_data
from pdf_bot.language import set_lang

SCALE_BY_KEY = 'scale_by'
SCALE_TO_KEY = 'scale_to'


def ask_scale_x(update, context):
    """
    Ask and wait for the horizontal scaling factor or the new width
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the horizontal scaling factor or the new width
    """
    _ = set_lang(update, context)
    message = update.effective_message

    if message.text == SCALE_BY:
        message.reply_text(_(
            'Send me the scaling factor for the horizontal axis. For example, 2 will double the horizontal axis and '
            '0.5 will half the horizontal axis.'), reply_markup=ReplyKeyboardRemove())

        return WAIT_SCALE_BY_X
    else:
        message.reply_text(_('Send me the new width.'), reply_markup=ReplyKeyboardRemove())

        return WAIT_SCALE_TO_X


@run_async
def ask_scale_by_y(update, context):
    """
    Validate the horizontal scaling factor, and ask and wait for the vertical scaling factor
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the horizontal or vertical scaling factor
    """
    _ = set_lang(update, context)
    message = update.effective_message
    scale_x = message.text

    try:
        scale_x = float(scale_x)
    except ValueError:
        message.reply_text(_('The scaling factor "{}" is invalid. Try again.').format(scale_x))

        return WAIT_SCALE_BY_X

    context.user_data[SCALE_BY_KEY] = scale_x
    message.reply_text(_(
        'Send me the scaling factor for the vertical axis. For example, 2 will double the vertical axis and '
        '0.5 will half the vertical axis.'))

    return WAIT_SCALE_BY_Y


@run_async
def pdf_scale_by(update, context):
    """
    Validate the vertical scaling factor and scale the PDF file
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the vertical scaling factor or the conversation has ended
    """
    if not check_user_data(update, context, PDF_INFO) or not check_user_data(update, context, SCALE_BY_KEY):
        return ConversationHandler.END

    _ = set_lang(update, context)
    message = update.effective_message
    scale_y = message.text
    
    try:
        scale_y = float(scale_y)
    except ValueError:
        message.reply_text(_('The scaling factor "{scale_y}" is invalid. Try again.'))

        return WAIT_SCALE_BY_Y

    user_data = context.user_data
    scale_x = user_data[SCALE_BY_KEY]
    message.reply_text(_('Scaling your PDF file, horizontally by {} and vertically by {}').format(scale_x, scale_y))
    process_pdf(update, context, 'scaled', scale_by=(scale_x, scale_y))

    # Clean up memory
    if user_data[SCALE_BY_KEY] == scale_x:
        del user_data[SCALE_BY_KEY]

    return ConversationHandler.END


@run_async
def ask_scale_to_y(update, context):
    """
    Validate the width, and ask and wait for the height
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the width or the height
    """
    _ = set_lang(update, context)
    message = update.effective_message
    scale_x = message.text

    try:
        scale_x = float(scale_x)
    except ValueError:
        message.reply_text(_('The width "{}" is invalid. Try again.').format(scale_x))

        return WAIT_SCALE_TO_X

    context.user_data[SCALE_TO_KEY] = scale_x
    message.reply_text(_('Send me the new height.'))

    return WAIT_SCALE_TO_Y


# Checks for height and scale PDF file
@run_async
def pdf_scale_to(update, context):
    """
    Validate the height and scale the PDF file
    Args:
        update: the update object
        context: the context object

    Returns:
        The variable indicating to wait for the height or the conversation has ended
    """
    if not check_user_data(update, context, PDF_INFO) or not check_user_data(update, context, SCALE_TO_KEY):
        return ConversationHandler.END

    _ = set_lang(update, context)
    message = update.effective_message
    scale_y = message.text

    try:
        scale_y = float(scale_y)
    except ValueError:
        message.reply_text(_('The height "{}" is invalid. Try again.').format(scale_y))

        return WAIT_SCALE_TO_Y

    user_data = context.user_data
    scale_x = user_data[SCALE_TO_KEY]
    message.reply_text(_('Scaling your PDF file with width of {} and height of {}').format(scale_x, scale_y))
    process_pdf(update, context, 'scaled', scale_to=(scale_x, scale_y))

    # Clean up memory
    if user_data[SCALE_TO_KEY] == scale_x:
        del user_data[SCALE_TO_KEY]

    return ConversationHandler.END
