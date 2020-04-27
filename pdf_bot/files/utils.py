from telegram import ReplyKeyboardMarkup
from telegram.ext import ConversationHandler

from pdf_bot.constants import BACK, PDF_INFO
from pdf_bot.utils import set_lang, check_user_data
from pdf_bot.files.document import ask_doc_task


def get_back_markup(update, context):
    _ = set_lang(update, context)
    reply_markup = ReplyKeyboardMarkup(
        [[_(BACK)]], one_time_keyboard=True, resize_keyboard=True
    )

    return reply_markup


def check_back_user_data(update, context):
    """
    Check for back action and if user data is valid
    Args:
        update: the update object
        context: the context object

    Returns:
        A state if it is a back action of the user data is invalid, else None
    """
    _ = set_lang(update, context)
    result = None

    if update.effective_message.text == _(BACK):
        result = ask_doc_task(update, context)
    elif not check_user_data(update, context, PDF_INFO):
        result = ConversationHandler.END

    return result
