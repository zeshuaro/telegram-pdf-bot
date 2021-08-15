import os
import re

from dotenv import load_dotenv
from telegram import (
    ChatAction,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    ReplyKeyboardRemove,
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
    update.effective_message.reply_chat_action(ChatAction.TYPING)
    _ = set_lang(update, context, query)
    keyboard = [
        [
            InlineKeyboardButton(
                _(PAYMENT_MSG).format(message=_(THANKS), emoji="😁", value="1"),
                callback_data=f"payment,{_(THANKS)},1",
            ),
            InlineKeyboardButton(
                _(PAYMENT_MSG).format(message=_(COFFEE), emoji="☕", value="3"),
                callback_data=f"payment,{_(COFFEE)},3",
            ),
        ],
        [
            InlineKeyboardButton(
                _(PAYMENT_MSG).format(message=_(BEER), emoji="🍺", value="5"),
                callback_data=f"payment,{_(BEER)},5",
            ),
            InlineKeyboardButton(
                _(PAYMENT_MSG).format(message=_(MEAL), emoji="🍲", value="10"),
                callback_data=f"payment,{_(MEAL)},10",
            ),
        ],
        [
            InlineKeyboardButton(
                _("Help translate PDF Bot"), "https://crwd.in/telegram-pdf-bot"
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query is None:
        user_id = update.effective_message.from_user.id
    else:
        user_id = query.from_user.id

    context.bot.send_message(
        user_id, _("Select how you want to support PDF Bot"), reply_markup=reply_markup
    )


def send_payment_invoice(
    update: Update,
    context: CallbackContext,
    query: CallbackQuery,
):
    message = query.message
    support_message, price = query.data.split(",")[1:]
    price = int(price)

    _ = set_lang(update, context)
    chat_id = message.chat_id
    title = _("Support PDF Bot")
    description = _("Say thanks to PDF Bot and help keep it running")
    prices = [LabeledPrice(support_message, price * 100)]

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
