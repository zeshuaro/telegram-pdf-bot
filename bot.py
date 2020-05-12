import logging
import os
import sys

from dotenv import load_dotenv
from logbook import Logger, StreamHandler
from logbook.compat import redirect_logging
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MessageEntity,
    ForceReply,
    ParseMode,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    Filters,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
)
from telegram.ext import messagequeue as mq
from telegram.ext.dispatcher import run_async
from telegram.utils.request import Request

from pdf_bot import *

load_dotenv()
APP_URL = os.environ.get("APP_URL")
PORT = int(os.environ.get("PORT", "8443"))
TELE_TOKEN = os.environ.get("TELE_TOKEN_BETA", os.environ.get("TELE_TOKEN"))
DEV_TELE_ID = int(os.environ.get("DEV_TELE_ID"))

TIMEOUT = 20
CALLBACK_DATA = "callback_data"


def main():
    # Setup logging
    logging.getLogger("pdfminer").setLevel(logging.WARNING)
    logging.getLogger("ocrmypdf").setLevel(logging.WARNING)
    redirect_logging()
    format_string = "{record.level_name}: {record.message}"
    StreamHandler(
        sys.stdout, format_string=format_string, level="INFO"
    ).push_application()
    log = Logger()

    q = mq.MessageQueue(all_burst_limit=3, all_time_limit_ms=3000)
    request = Request(con_pool_size=8)
    pdf_bot = MQBot(TELE_TOKEN, request=request, mqueue=q)

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(
        bot=pdf_bot,
        use_context=True,
        request_kwargs={"connect_timeout": TIMEOUT, "read_timeout": TIMEOUT},
    )

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # General commands handlers
    dispatcher.add_handler(CommandHandler("start", start_msg))
    dispatcher.add_handler(CommandHandler("help", help_msg))
    dispatcher.add_handler(CommandHandler("setlang", send_lang))
    dispatcher.add_handler(CommandHandler("support", send_support_options_with_async))
    dispatcher.add_handler(CommandHandler("send", send_msg, Filters.user(DEV_TELE_ID)))
    dispatcher.add_handler(
        CommandHandler("stats", get_stats, Filters.user(DEV_TELE_ID))
    )

    # Callback query handler
    dispatcher.add_handler(CallbackQueryHandler(process_callback_query))

    # Payment handlers
    dispatcher.add_handler(
        MessageHandler(Filters.reply & Filters.text, receive_custom_amount)
    )
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_check))
    dispatcher.add_handler(
        MessageHandler(Filters.successful_payment, successful_payment)
    )

    # URL handler
    dispatcher.add_handler(
        MessageHandler(Filters.entity(MessageEntity.URL), url_to_pdf)
    )

    # PDF commands handlers
    dispatcher.add_handler(compare_cov_handler())
    dispatcher.add_handler(merge_cov_handler())
    dispatcher.add_handler(photo_cov_handler())
    dispatcher.add_handler(text_cov_handler())
    dispatcher.add_handler(watermark_cov_handler())

    # PDF file handler
    dispatcher.add_handler(file_cov_handler())

    # Feedback handler
    dispatcher.add_handler(feedback_cov_handler())

    # Log all errors
    dispatcher.add_error_handler(error_callback)

    # Start the Bot
    if APP_URL is not None:
        updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TELE_TOKEN)
        updater.bot.set_webhook(APP_URL + TELE_TOKEN)
        log.notice("Bot started webhook")
    else:
        updater.start_polling()
        log.notice("Bot started polling")

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


@run_async
def start_msg(update, context):
    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _(
            "Welcome to PDF Bot!\n\n*Features*\n"
            "- Compare, crop, decrypt, encrypt, merge, rotate, scale, split and "
            "add a watermark to a PDF file\n"
            "- Extract text and photos in a PDF file and convert a PDF file into photos\n"
            "- Beautify and convert photos into PDF format\n"
            "- Convert a web page into a PDF file\n\n"
            "Type /help to see how to use PDF Bot"
        ),
        parse_mode=ParseMode.MARKDOWN,
    )

    # Create the user entity in Datastore
    create_user(update.effective_message.from_user.id)


@run_async
def help_msg(update, context):
    _ = set_lang(update, context)
    keyboard = [
        [InlineKeyboardButton(_("Set Language"), callback_data=SET_LANG)],
        [
            InlineKeyboardButton(_("Join Channel"), f"https://t.me/{CHANNEL_NAME}"),
            InlineKeyboardButton(_("Support PDF Bot"), callback_data=PAYMENT),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.effective_message.reply_text(
        _(
            "You can perform most of the tasks simply by sending me a PDF file, a photo or "
            "a link to a web page.\n\n"
            "Some tasks can be performed by using the commands /compare, /merge, /watermark or /photo"
        ),
        reply_markup=reply_markup,
    )


@run_async
def process_callback_query(update, context):
    _ = set_lang(update, context)
    query = update.callback_query
    data = query.data

    if CALLBACK_DATA not in context.user_data:
        context.user_data[CALLBACK_DATA] = set()

    if data not in context.user_data[CALLBACK_DATA]:
        context.user_data[CALLBACK_DATA].add(data)
        if data == SET_LANG:
            send_lang(update, context, query)
        elif data in LANGUAGES:
            store_lang(update, context, query)
        if data == PAYMENT:
            send_support_options_without_async(update, context, query)
        elif data in [THANKS, COFFEE, BEER, MEAL]:
            send_payment_invoice(update, context, query)
        elif data == CUSTOM:
            context.bot.send_message(
                query.from_user.id,
                _("Send me the amount that you'll like to support PDF Bot"),
                reply_markup=ForceReply(),
            )

        context.user_data[CALLBACK_DATA].remove(data)


def send_msg(update, context):
    tele_id = int(context.args[0])
    message = " ".join(context.args[1:])

    try:
        context.bot.send_message(tele_id, message)
    except Exception as e:
        log = Logger()
        log.error(e)
        update.effective_message.reply_text(DEV_TELE_ID, "Failed to send message")


def error_callback(update, context):
    log = Logger()
    log.error(f'Update "{update}" caused error "{context.error}"')


if __name__ == "__main__":
    main()
