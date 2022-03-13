import os
from http import HTTPStatus

from dotenv import load_dotenv
from flask import Flask, Response, request
from telegram import Update
from telegram.ext import messagequeue as mq
from telegram.ext.dispatcher import Dispatcher
from telegram.utils.request import Request

import pdf_bot.dispatcher as dp
import pdf_bot.logging as log
from pdf_bot.mq_bot import MQBot

load_dotenv()
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")


def create_app():
    log.setup_logging()

    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    q = mq.MessageQueue(all_burst_limit=3, all_time_limit_ms=3000)
    req = Request(con_pool_size=8, connect_timeout=10, read_timeout=10)
    bot = MQBot(TELEGRAM_TOKEN, request=req, mqueue=q)

    dispatcher = Dispatcher(bot=bot, update_queue=None, workers=0)
    dp.setup_dispatcher(dispatcher)

    @app.route("/", methods=["POST"])
    def index() -> Response:
        dispatcher.process_update(Update.de_json(request.get_json(force=True), bot))

        return Response("", HTTPStatus.NO_CONTENT)

    return app
