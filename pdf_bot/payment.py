import os
import re

from dotenv import load_dotenv
from telegram import LabeledPrice, ReplyKeyboardMarkup, ReplyKeyboardRemove

from pdf_bot.constants import PAYMENT_THANKS, PAYMENT_COFFEE, PAYMENT_BEER, PAYMENT_MEAL, PAYMENT_CUSTOM, \
    PAYMENT_DICT, PAYMENT_PAYLOAD, PAYMENT_PARA, PAYMENT_CURRENCY

load_dotenv()
STRIPE_TOKEN = os.environ.get('STRIPE_TOKEN', os.environ.get('STRIPE_TOKEN_BETA'))


def send_payment_options(update, context, user_id=None):
    keyboard = [[PAYMENT_THANKS, PAYMENT_COFFEE, PAYMENT_BEER], [PAYMENT_MEAL, PAYMENT_CUSTOM]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    text = 'Select how you want to support PDF Bot'

    if user_id is None:
        update.message.reply_text(text, reply_markup=reply_markup)
    else:
        context.bot.send_message(user_id, text, reply_markup=reply_markup)


def payment_callback(update, context):
    chat_id = update.message.chat_id
    title = "Support PDF Bot"
    description = "Say thanks to PDF Bot and help keep it running"
    payload = PAYMENT_PAYLOAD
    provider_token = STRIPE_TOKEN
    start_parameter = PAYMENT_PARA
    currency = PAYMENT_CURRENCY
    price = PAYMENT_DICT[update.message.text]
    prices = [LabeledPrice(re.sub(r'\s\(.*', '', update.message.text), price * 100)]

    context.bot.send_invoice(chat_id, title, description, payload, provider_token, start_parameter, currency, prices)


def precheckout_callback(update, _):
    query = update.pre_checkout_query
    if query.invoice_payload != PAYMENT_PAYLOAD:
        query.answer(ok=False, error_message="Something went wrong")
    else:
        query.answer(ok=True)


def successful_payment_callback(update, _):
    update.message.reply_text('Thank you for your support!', reply_markup=ReplyKeyboardRemove())
