import os

from dotenv import load_dotenv
from logbook import Logger
from telegram.ext import Updater
from telegram.ext import messagequeue as mq
from telegram.utils.request import Request

import pdf_bot.dispatcher as dp
import pdf_bot.logging as pdf_bot_logging
from pdf_bot.mq_bot import MQBot

load_dotenv()
TELE_TOKEN = os.environ.get("TELE_TOKEN")

TIMEOUT = 20


def main():
    # Setup logging
    pdf_bot_logging.setup_logging()

    q = mq.MessageQueue(all_burst_limit=3, all_time_limit_ms=3000)
    request = Request(con_pool_size=8)
    pdf_bot = MQBot(TELE_TOKEN, request=request, mqueue=q)

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(
        bot=pdf_bot,
        use_context=True,
        request_kwargs={"connect_timeout": TIMEOUT, "read_timeout": TIMEOUT},
    )

    dispatcher = updater.dispatcher
    dp.setup_dispatcher(dispatcher)

    updater.start_polling()
    log = Logger()
    log.notice("Bot started polling")

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == "__main__":
    main()
