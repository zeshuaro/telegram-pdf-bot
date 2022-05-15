import os

from dotenv import load_dotenv
from loguru import logger
from telegram.ext import Updater

import pdf_bot.dispatcher as dp
import pdf_bot.logging as pdf_bot_logging

load_dotenv()
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
APP_URL = os.environ.get("APP_URL")
PORT = int(os.environ.get("PORT", "8443"))

TIMEOUT = 30


def main():
    # Setup logging
    pdf_bot_logging.setup_logging()

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(
        token=TELEGRAM_TOKEN,
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
