import os
import re

from dotenv import load_dotenv
from telegram import LabeledPrice, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, MessageHandler, CommandHandler, Filters
from telegram.ext.dispatcher import run_async

from pdf_bot.constants import PAYMENT_THANKS, PAYMENT_COFFEE, PAYMENT_BEER, PAYMENT_MEAL, PAYMENT_CUSTOM, \
    PAYMENT_DICT, PAYMENT_PAYLOAD, PAYMENT_PARA, PAYMENT_CURRENCY, WAIT_PAYMENT
from pdf_bot.utils import cancel, get_lang

load_dotenv()
STRIPE_TOKEN = os.environ.get('STRIPE_TOKEN', os.environ.get('STRIPE_TOKEN_BETA'))


def payment_cov_handler():
    """
    Create a payment conversation handler object
    Returns:
        The conversation handler object
    """
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex(rf'^{re.escape(PAYMENT_CUSTOM)}$'), custom_amount)],
        states={
            WAIT_PAYMENT: [MessageHandler(Filters.text, receive_custom_amount)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    return conv_handler


@run_async
def custom_amount(update, context):
    _ = get_lang(update, context)
    update.effective_message.reply_text(_('Send me the amount that you\'ll like to support PDF Bot or /cancel this.'),
                                        reply_markup=ReplyKeyboardRemove())

    return WAIT_PAYMENT


@run_async
def receive_custom_amount(update, context):
    try:
        amount = round(float(update.effective_message.text))
        if amount <= 0:
            raise ValueError
    except ValueError:
        _ = get_lang(update, context)
        update.effective_message.reply_text(_('The amount you sent is invalid, try again.'))

        return WAIT_PAYMENT

    return send_payment_invoice(update, context, amount)


@run_async
def send_payment_options(update, context, user_id=None):
    _ = get_lang(update, context)
    keyboard = [[InlineKeyboardButton(_(PAYMENT_THANKS), callback_data=PAYMENT_THANKS),
                 InlineKeyboardButton(_(PAYMENT_COFFEE), callback_data=PAYMENT_COFFEE)],
                [InlineKeyboardButton(_(PAYMENT_BEER), callback_data=PAYMENT_BEER),
                 InlineKeyboardButton(_(PAYMENT_MEAL), callback_data=PAYMENT_MEAL)],
                [InlineKeyboardButton(_(PAYMENT_CUSTOM), callback_data=PAYMENT_CUSTOM)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = _('Select how you want to support PDF Bot')

    if user_id is None:
        update.effective_message.reply_text(text, reply_markup=reply_markup)
    else:
        context.bot.send_message(user_id, text, reply_markup=reply_markup)


def send_payment_invoice(update, context, query=None, amount=None):
    if query is None:
        message = update.effective_message
        label = message.text
    else:
        message = query.message
        label = query.data

    _ = get_lang(update, context)
    chat_id = message.chat_id
    title = _('Support PDF Bot')
    description = _('Say thanks to PDF Bot and help keep it running')

    if amount is None:
        price = PAYMENT_DICT[label]
    else:
        label = PAYMENT_CUSTOM
        price = amount

    prices = [LabeledPrice(re.sub(r'\s\(.*', '', label), price * 100)]

    context.bot.send_invoice(
        chat_id, title, description, PAYMENT_PAYLOAD, STRIPE_TOKEN, PAYMENT_PARA, PAYMENT_CURRENCY, prices)


@run_async
def precheckout_check(update, context):
    _ = get_lang(update, context)
    query = update.pre_checkout_query

    if query.invoice_payload != PAYMENT_PAYLOAD:
        query.answer(ok=False, error_message=_('Something went wrong'))
    else:
        query.answer(ok=True)


def successful_payment(update, context):
    _ = get_lang(update, context)
    update.effective_message.reply_text(_('Thank you for your support!'), reply_markup=ReplyKeyboardRemove())
