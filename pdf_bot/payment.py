import os
import re

from dotenv import load_dotenv
from telegram import (
    LabeledPrice,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.callbackquery import CallbackQuery
from telegram.ext import CallbackContext

from pdf_bot.constants import *
from pdf_bot.language import set_lang

load_dotenv()
STRIPE_TOKEN = os.environ.get("STRIPE_TOKEN", os.environ.get("STRIPE_TOKEN_BETA"))


def send_support_options(
    update: Update, context: CallbackContext, query: CallbackQuery = None
):
    _ = set_lang(update, context, query)
    keyboard = [
        [
            InlineKeyboardButton(_(THANKS), callback_data=THANKS),
            InlineKeyboardButton(_(COFFEE), callback_data=COFFEE),
        ],
        [
            InlineKeyboardButton(_(BEER), callback_data=BEER),
            InlineKeyboardButton(_(MEAL), callback_data=MEAL),
        ],
        [
            InlineKeyboardButton(
                _("Help translate PDF Bot"), "https://crwd.in/telegram-pdf-bot"
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = _("Select how you want to support PDF Bot")

    if query is None:
        user_id = update.effective_message.from_user.id
    else:
        user_id = query.from_user.id

    context.bot.send_message(user_id, text, reply_markup=reply_markup)


def send_payment_invoice(
    update: Update,
    context: CallbackContext,
    query: CallbackQuery,
):
    if query is None:
        message = update.effective_message
        label = message.text
    else:
        message = query.message
        label = query.data

    _ = set_lang(update, context)
    chat_id = message.chat_id
    title = _("Support PDF Bot")
    description = _("Say thanks to PDF Bot and help keep it running")

    price = PAYMENT_DICT[label]
    prices = [LabeledPrice(re.sub(r"\s\(.*", "", label), price * 100)]

    context.bot.send_invoice(
        chat_id,
        title,
        description,
        PAYMENT_PAYLOAD,
        STRIPE_TOKEN,
        CURRENCY,
        prices,
        max_tip_amount=1000,
        suggested_tip_amounts=[100, 300, 500, 1000],
    )


def precheckout_check(update: Update, context: CallbackContext):
    _ = set_lang(update, context)
    query = update.pre_checkout_query

    if query.invoice_payload != PAYMENT_PAYLOAD:
        query.answer(ok=False, error_message=_("Something went wrong"))
    else:
        query.answer(ok=True)


def successful_payment(update: Update, context: CallbackContext):
    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _("Thank you for your support!"), reply_markup=ReplyKeyboardRemove()
    )
