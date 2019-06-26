import logbook
import os
import sys

from dotenv import load_dotenv
from feedback_bot import feedback_cov_handler
from logbook import Logger, StreamHandler

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, Filters
from telegram.ext.dispatcher import run_async

from file import file_cov_handler
from merge import merge_cov_handler
from photo import photo_cov_handler
from watermark import watermark_cov_handler

load_dotenv()
APP_URL = os.environ.get("APP_URL")
PORT = int(os.environ.get('PORT', '8443'))
TELE_TOKEN = os.environ.get('TELE_TOKEN_BETA', os.environ.get('TELE_TOKEN'))
DEV_TELE_ID = int(os.environ.get('DEV_TELE_ID'))
DEV_EMAIL = os.environ.get('DEV_EMAIL', 'sample@email.com')

CHANNEL_NAME = 'pdf2botdev'
BOT_NAME = 'pdf2bot'
TIMEOUT = 20


def main():
    # Setup logging
    logbook.set_datetime_format('local')
    format_string = '[{record.time:%Y-%m-%d %H:%M:%S}] {record.level_name}: {record.message}'
    StreamHandler(sys.stdout, format_string=format_string).push_application()
    log = Logger()

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(
        TELE_TOKEN, use_context=True, request_kwargs={'connect_timeout': TIMEOUT, 'read_timeout': TIMEOUT})

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler('start', start_msg))
    dispatcher.add_handler(CommandHandler('help', help_msg))
    dispatcher.add_handler(CommandHandler('donate', donate_msg))
    # dispatcher.add_handler(compare_cov_handler())
    dispatcher.add_handler(merge_cov_handler())
    dispatcher.add_handler(photo_cov_handler())
    dispatcher.add_handler(watermark_cov_handler())
    dispatcher.add_handler(file_cov_handler())
    dispatcher.add_handler(feedback_cov_handler())
    dispatcher.add_handler(CommandHandler('send', send, Filters.user(DEV_TELE_ID), pass_args=True))

    # log all errors
    dispatcher.add_error_handler(error_callback)

    # Start the Bot
    if APP_URL is not None:
        updater.start_webhook(listen='0.0.0.0', port=PORT, url_path=TELE_TOKEN)
        print(APP_URL, TELE_TOKEN)
        updater.bot.set_webhook(APP_URL + TELE_TOKEN)
        log.notice('Bot started webhook')
    else:
        updater.start_polling()
        log.notice('Bot started polling')

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


# @run_async
def start_msg(update, _):
    """
    Send start message
    Args:
        update: the update object
        _: unused variable

    Returns:
        None
    """
    text = 'Welcome to PDF Bot!\n\n'
    text += 'I can compare, decrypt, encrypt, merge, rotate, scale, split and add watermark to a PDF file.\n\n '
    text += 'I can also extract images in a PDF file and convert a PDF file into images.\n\n'
    text += 'I can also also beautify and convert photos into PDF format.\n\n'
    text += 'Type /help to see how to use me.'

    update.message.reply_text(text)


@run_async
def help_msg(update, _):
    """
    Send help message
    Args:
        update: the update object
        _: unused variable

    Returns:
        None
    """
    text = 'You can perform most of the tasks simply by sending me a PDF file. You can then select a task and I ' \
           'will guide you through each of the tasks.\n\n'
    text += 'If you want to compare, merge or add watermark to PDF files, you will have to use the /compare, ' \
            '/merge or /watermark commands respectively.\n\n'
    text += 'If you want to beautify and convert photos into PDF format, simply send me a photo or ' \
            'use the /photo command to deal with multiple photos.\n\n'
    text += 'Please note that I can only download files up to 20 MB in size and upload files up to 50 MB in size. ' \
            'If the result files are too large, I will not be able to send you the file.\n\n'

    keyboard = [[InlineKeyboardButton('Join Channel', f'https://t.me/{CHANNEL_NAME}'),
                 InlineKeyboardButton('Rate me', f'https://t.me/storebot?start={BOT_NAME}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(text, reply_markup=reply_markup)


@run_async
def donate_msg(update, _):
    """
    Send donate message
    Args:
        update: the update object
        _: unused variable

    Returns:
        None
    """
    text = f'Want to help keep me online? Please donate to {DEV_EMAIL} through PayPal.\n\n' \
           f'Donations help me to stay on my server and keep running.'

    update.message.reply_text(text)


# Sends a message to a specified user
def send(bot, update, args):
    tele_id = int(args[0])
    message = ' '.join(args[1:])

    try:
        bot.send_message(tele_id, message)
    except Exception as e:
        LOGGER.exception(e)
        bot.send_message(DEV_TELE_ID, 'Failed to send message')


def error_callback(update, context):
    log = Logger()
    log.error(f'Update "{update}" caused error "{context.error}"')


if __name__ == '__main__':
    main()
