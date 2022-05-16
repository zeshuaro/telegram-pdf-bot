import os

import sentry_sdk
from dotenv import load_dotenv
from loguru import logger
from telegram.ext import Updater

import pdf_bot.dispatcher as dp
import pdf_bot.logging as pdf_bot_logging

load_dotenv()
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
SENTRY_DSN = os.environ.get("SENTRY_DSN")
APP_URL = os.environ.get("APP_URL")
PORT = int(os.environ.get("PORT", "8443"))

TIMEOUT = 30


def main():
    pdf_bot_logging.setup_logging()
    if SENTRY_DSN is not None:
        sentry_sdk.init(SENTRY_DSN, traces_sample_rate=1.0)

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

    updater.idle()


if __name__ == "__main__":
    main()
