from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler

from pdf_bot.constants import (
    WAIT_ROTATE_DEGREE,
    PDF_INFO,
    ROTATE_90,
    ROTATE_180,
    ROTATE_270,
    BACK,
)
from pdf_bot.utils import process_pdf, check_user_data
from pdf_bot.language import set_lang
from pdf_bot.files.document import ask_doc_task


def ask_rotate_degree(update, context):
    _ = set_lang(update, context)
    keyboard = [[ROTATE_90, ROTATE_180], [ROTATE_270, _(BACK)]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=True
    )
    update.effective_message.reply_text(
        _("Select the degrees that you'll like to rotate your PDF file in clockwise"),
        reply_markup=reply_markup,
    )

    return WAIT_ROTATE_DEGREE


def check_rotate_degree(update, context):
    _ = set_lang(update, context)
    text = update.effective_message.text

    if text in [_(ROTATE_90), _(ROTATE_180), _(ROTATE_270)]:
        return rotate_pdf(update, context)
    elif text == _(BACK):
        return ask_doc_task(update, context)


def rotate_pdf(update, context):
    if not check_user_data(update, context, PDF_INFO):
        return ConversationHandler.END

    _ = set_lang(update, context)
    degree = int(update.effective_message.text)
    update.effective_message.reply_text(
        _("Rotating your PDF file clockwise by {} degrees").format(degree),
        reply_markup=ReplyKeyboardRemove(),
    )
    process_pdf(update, context, "rotated", rotate_degree=degree)

    return ConversationHandler.END
