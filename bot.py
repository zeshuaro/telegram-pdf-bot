import datetime as dt
import logging
import os
import sys
from threading import Thread

from dotenv import load_dotenv
from logbook import Logger, StreamHandler
from logbook.compat import redirect_logging
from telegram import (
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MessageEntity,
    ParseMode,
    Update,
)
from telegram.chataction import ChatAction
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    PreCheckoutQueryHandler,
    Updater,
)
from telegram.error import Unauthorized
from telegram.ext import messagequeue as mq
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

    def stop_and_restart():
        updater.stop()
        os.execl(sys.executable, sys.executable, *sys.argv)

    def restart(_):
        Thread(target=stop_and_restart).start()

    job_queue = updater.job_queue
    job_queue.run_repeating(restart, interval=dt.timedelta(hours=1))

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # General commands handlers
    dispatcher.add_handler(CommandHandler("start", start_msg, run_async=True))
    dispatcher.add_handler(CommandHandler("help", help_msg, run_async=True))
    dispatcher.add_handler(CommandHandler("setlang", send_lang, run_async=True))
    dispatcher.add_handler(
        CommandHandler("support", send_support_options, run_async=True)
    )
    dispatcher.add_handler(CommandHandler("send", send_msg, Filters.user(DEV_TELE_ID)))
    dispatcher.add_handler(
        CommandHandler("stats", get_stats, Filters.user(DEV_TELE_ID))
    )

    # Callback query handler
    dispatcher.add_handler(CallbackQueryHandler(process_callback_query, run_async=True))

    # Payment handlers
    dispatcher.add_handler(
        MessageHandler(
            Filters.reply & TEXT_FILTER, receive_custom_amount, run_async=True
        )
    )
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_check, run_async=True))
    dispatcher.add_handler(
        MessageHandler(Filters.successful_payment, successful_payment, run_async=True)
    )

    # URL handler
    dispatcher.add_handler(
        MessageHandler(Filters.entity(MessageEntity.URL), url_to_pdf, run_async=True)
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


def start_msg(update: Update, context: CallbackContext) -> None:
    update.effective_message.chat.send_action(ChatAction.TYPING)

    # Create the user entity in Datastore
    create_user(update.effective_message.from_user)

    _ = set_lang(update, context)
    update.effective_message.reply_text(
        _(
            "Welcome to PDF Bot!\n\n<b>Key features:</b>\n"
            "- Compress, merge, preview, rename, split and add watermark to PDF files\n"
            "- Create PDF files from text messages\n"
            "- Extract images and text from PDF files\n"
            "- Convert PDF files into images\n"
            "- Convert webpages and images into PDF files\n"
            "- Beautify handwritten notes images into PDF files\n"
            "- <b><i>And more...</i></b>\n\n"
            "Type /help to see how to use PDF Bot"
        ),
        parse_mode=ParseMode.HTML,
    )


def help_msg(update, context):
    update.effective_message.chat.send_action(ChatAction.TYPING)
    _ = set_lang(update, context)
    keyboard = [
        [InlineKeyboardButton(_("Set Language 🌎"), callback_data=SET_LANG)],
        [
            InlineKeyboardButton(_("Join Channel"), f"https://t.me/{CHANNEL_NAME}"),
            InlineKeyboardButton(_("Support PDF Bot"), callback_data=PAYMENT),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.effective_message.reply_text(
        _(
            "You can perform most of the tasks by sending me one of the followings:\n"
            "- PDF files\n- Photos\n- Webpage links\n\n"
            "The rest of the tasks can be performed by using the commands below:\n"
            "/compare - compare PDF files\n"
            "/merge - merge PDF files\n"
            "/photo - convert and combine multiple photos into PDF files\n"
            "/text - create PDF files from text messages\n"
            "/watermark - add watermark to PDF files"
        ),
        reply_markup=reply_markup,
    )


def process_callback_query(update: Update, context: CallbackContext):
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
            send_support_options(update, context, query)
        elif data in [THANKS, COFFEE, BEER, MEAL]:
            send_payment_invoice(update, context, query)
        elif data == CUSTOM:
            context.bot.send_message(
                query.from_user.id,
                _("Send me the amount that you'll like to support PDF Bot"),
                reply_markup=ForceReply(),
            )

        context.user_data[CALLBACK_DATA].remove(data)

    query.answer()


def send_msg(update: Update, context: CallbackContext):
    tele_id = int(context.args[0])
    message = " ".join(context.args[1:])

    try:
        context.bot.send_message(tele_id, message)
        update.effective_message.reply_text("Message sent")
    except Exception as e:
        log = Logger()
        log.error(e)
        update.effective_message.reply_text("Failed to send message")


def error_callback(update: Update, context: CallbackContext):
    if context.error is not Unauthorized:
        log = Logger()
        log.error(f'Update "{update}" caused error "{context.error}"')


if __name__ == "__main__":
    main()
