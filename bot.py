import logbook
import os
import sys

from dotenv import load_dotenv
from logbook import Logger, StreamHandler
from logbook.compat import redirect_logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, ForceReply
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, CallbackQueryHandler, PreCheckoutQueryHandler
from telegram.ext.dispatcher import run_async
from telegram.parsemode import ParseMode

from pdf_bot import *

load_dotenv()
APP_URL = os.environ.get("APP_URL")
PORT = int(os.environ.get('PORT', '8443'))
TELE_TOKEN = os.environ.get('TELE_TOKEN_BETA', os.environ.get('TELE_TOKEN'))
DEV_TELE_ID = int(os.environ.get('DEV_TELE_ID'))
DEV_EMAIL = os.environ.get('DEV_EMAIL', 'sample@email.com')

TIMEOUT = 20


def main():
    # Setup logging
    redirect_logging()
    logbook.set_datetime_format('local')
    format_string = '{record.level_name}: {record.message}'
    StreamHandler(sys.stdout, format_string=format_string, level='INFO').push_application()
    log = Logger()

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(
        TELE_TOKEN, use_context=True, request_kwargs={'connect_timeout': TIMEOUT, 'read_timeout': TIMEOUT})

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # General commands handlers
    dispatcher.add_handler(CommandHandler('start', start_msg))
    dispatcher.add_handler(CommandHandler('help', help_msg))
    dispatcher.add_handler(CommandHandler('setlang', send_lang))
    dispatcher.add_handler(CommandHandler('donate', send_payment_options))
    dispatcher.add_handler(CommandHandler('send', send_msg, Filters.user(DEV_TELE_ID)))
    dispatcher.add_handler(CommandHandler('stats', get_stats, Filters.user(DEV_TELE_ID)))

    # Callback query handler
    dispatcher.add_handler(CallbackQueryHandler(process_callback_query))

    # Payment handlers
    dispatcher.add_handler(MessageHandler(Filters.reply & Filters.text, receive_custom_amount))
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_check))
    dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment))

    # URL handler
    dispatcher.add_handler(MessageHandler(Filters.entity(MessageEntity.URL), url_to_pdf))

    # PDF commands handlers
    dispatcher.add_handler(compare_cov_handler())
    dispatcher.add_handler(merge_cov_handler())
    dispatcher.add_handler(photo_cov_handler())
    dispatcher.add_handler(watermark_cov_handler())

    # PDF file handler
    dispatcher.add_handler(file_cov_handler())

    # Feedback handler
    dispatcher.add_handler(feedback_cov_handler())

    # Log all errors
    dispatcher.add_error_handler(error_callback)

    # Start the Bot
    if APP_URL is not None:
        updater.start_webhook(listen='0.0.0.0', port=PORT, url_path=TELE_TOKEN)
        updater.bot.set_webhook(APP_URL + TELE_TOKEN)
        log.notice('Bot started webhook')
    else:
        updater.start_polling()
        log.notice('Bot started polling')

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


@run_async
def start_msg(update, context):
    _ = set_lang(update, context)
    update.effective_message.reply_text(_(
        'Welcome to PDF Bot!\n\n*Features*\n'
        '- Compare, crop, decrypt, encrypt, merge, rotate, scale, split and add a watermark to a PDF file\n'
        '- Extract images in a PDF file and convert a PDF file into images\n'
        '- Beautify and convert photos into PDF format\n'
        '- Convert a web page into a PDF file\n\n'
        'Type /help to see how to use PDF Bot.'), parse_mode=ParseMode.MARKDOWN)

    # Create the user entity in Datastore
    create_user(update.effective_message.from_user.id)


@run_async
def help_msg(update, context):
    _ = set_lang(update, context)
    keyboard = [[InlineKeyboardButton(_('Set Language'), callback_data=SET_LANG)],
                [InlineKeyboardButton(_('Join Channel'), f'https://t.me/{CHANNEL_NAME}'),
                 InlineKeyboardButton(_('Support PDF Bot'), callback_data=PAYMENT)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.effective_message.reply_text(_(
        'You can perform most of the tasks simply by sending me a PDF file, a photo or a link to a web page.\n\n'
        'Some tasks can be performed by using the commands /compare, /merge, /watermark or /photo.'),
        reply_markup=reply_markup)


@run_async
def process_callback_query(update, context):
    _ = set_lang(update, context)
    query = update.callback_query

    if query.data == SET_LANG:
        send_lang(update, context, query)
    elif query.data in LANGUAGES:
        store_lang(update, context, query)
    if query.data == PAYMENT:
        send_payment_options(update, context, query)
    elif query.data in [THANKS, COFFEE, BEER, MEAL]:
        send_payment_invoice(update, context, query)
    elif query.data == CUSTOM:
        context.bot.send_message(
            query.from_user.id, _('Send me the amount that you\'ll like to support PDF Bot'), reply_markup=ForceReply())


def send_msg(update, context):
    tele_id = int(context.args[0])
    message = ' '.join(context.args[1:])

    try:
        context.bot.send_message(tele_id, message)
    except Exception as e:
        log = Logger()
        log.error(e)
        update.effective_message.reply_text(DEV_TELE_ID, 'Failed to send message')


def error_callback(update, context):
    log = Logger()
    log.error(f'Update "{update}" caused error "{context.error}"')


if __name__ == '__main__':
    main()
