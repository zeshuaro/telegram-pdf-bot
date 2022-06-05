from telegram import ReplyKeyboardRemove
from telegram.ext import ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.consts import WAIT_ENCRYPT_PW
from pdf_bot.files.utils import check_back_user_data, get_back_markup
from pdf_bot.language import set_lang
from pdf_bot.utils import process_pdf


def ask_encrypt_pw(update, context):
    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Send me the password to encrypt your PDF file"),
        reply_markup=get_back_markup(update, context),
    )

    return WAIT_ENCRYPT_PW


def encrypt_pdf(update, context):
    result = check_back_user_data(update, context)
    if result is not None:
        return result

    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Encrypting your PDF file"), reply_markup=ReplyKeyboardRemove()
    )
    process_pdf(
        update, context, TaskType.encrypt_pdf, encrypt_pw=update.effective_message.text
    )

    return ConversationHandler.END
