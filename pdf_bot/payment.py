import os
import re

from dotenv import load_dotenv
from telegram import LabeledPrice, ReplyKeyboardRemove, InlineKeyboardButton, \
    InlineKeyboardMarkup, ForceReply
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import *
from pdf_bot.language import set_lang

load_dotenv()
STRIPE_TOKEN = os.environ.get('STRIPE_TOKEN', os.environ.get('STRIPE_TOKEN_BETA'))


@run_async
def receive_custom_amount(update, context):
    _ = set_lang(update, context)
    if _(CUSTOM_MSG) in update.effective_message.reply_to_message.text:
        try:
            amount = round(float(update.effective_message.text))
            if amount <= 0:
                raise ValueError

            send_payment_invoice(update, context, amount=amount)
        except ValueError:
            _ = set_lang(update, context)
            update.effective_message.reply_text(_(
                'The amount you sent is invalid, try again. {}').format(_(CUSTOM_MSG)),
                reply_markup=ForceReply())


def send_support_options_without_async(update, context, query=None):
    _ = set_lang(update, context, query)
    keyboard = [[InlineKeyboardButton(_(THANKS), callback_data=THANKS),
                 InlineKeyboardButton(_(COFFEE), callback_data=COFFEE)],
                [InlineKeyboardButton(_(BEER), callback_data=BEER),
                 InlineKeyboardButton(_(MEAL), callback_data=MEAL)],
                [InlineKeyboardButton(_(CUSTOM), callback_data=CUSTOM)],
                [InlineKeyboardButton(_('Help translate PDF Bot'),
                                      'https://crwd.in/telegram-pdf-bot')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = _('Select how you want to support PDF Bot')

    if query is None:
        user_id = update.effective_message.from_user.id
    else:
        user_id = query.from_user.id

    context.bot.send_message(user_id, text, reply_markup=reply_markup)


@run_async
def send_support_options_with_async(update, context, query=None):
    send_support_options_without_async(update, context, query)


def send_payment_invoice(update, context, query=None, amount=None):
    if query is None:
        message = update.effective_message
        label = message.text
    else:
        message = query.message
        label = query.data

    _ = set_lang(update, context)
    chat_id = message.chat_id
    title = _('Support PDF Bot')
    description = _('Say thanks to PDF Bot and help keep it running')

    if amount is None:
        price = PAYMENT_DICT[label]
    else:
        label = CUSTOM
        price = amount

    prices = [LabeledPrice(re.sub(r'\s\(.*', '', label), price * 100)]

    context.bot.send_invoice(
        chat_id, title, description, PAYMENT_PAYLOAD, STRIPE_TOKEN, PAYMENT_PARA, CURRENCY, prices)


@run_async
def precheckout_check(update, context):
    _ = set_lang(update, context)
    query = update.pre_checkout_query

    if query.invoice_payload != PAYMENT_PAYLOAD:
        query.answer(ok=False, error_message=_('Something went wrong'))
    else:
        query.answer(ok=True)


def successful_payment(update, context):
    _ = set_lang(update, context)
    update.effective_message.reply_text(_('Thank you for your support!'),
                                        reply_markup=ReplyKeyboardRemove())
