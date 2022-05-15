import os

from dotenv import load_dotenv
from loguru import logger
from telegram.ext import Updater
from telegram.ext import messagequeue as mq
from telegram.utils.request import Request

import pdf_bot.dispatcher as dp
import pdf_bot.logging as pdf_bot_logging
from pdf_bot.mq_bot import MQBot

load_dotenv()
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
APP_URL = os.environ.get("APP_URL")
PORT = int(os.environ.get("PORT", "8443"))

TIMEOUT = 30


def main():
    # Setup logging
    pdf_bot_logging.setup_logging()

    q = mq.MessageQueue(all_burst_limit=3, all_time_limit_ms=3000)
    request = Request(con_pool_size=12, connect_timeout=TIMEOUT, read_timeout=TIMEOUT)
    pdf_bot = MQBot(TELEGRAM_TOKEN, request=request, mqueue=q)

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(
        bot=pdf_bot,
        use_context=True,
        request_kwargs={"connect_timeout": TIMEOUT, "read_timeout": TIMEOUT},
        workers=8,
    )

    dispatcher = updater.dispatcher
    dp.setup_dispatcher(dispatcher)

    if APP_URL is not None:
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_TOKEN,
            webhook_url=f"{APP_URL}/{TELEGRAM_TOKEN}",
        )
        logger.info("Bot started webhook")
    else:
        updater.start_polling()
        logger.info("Bot started polling")

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == "__main__":
    main()
