import logging

import sentry_sdk
from dependency_injector.providers import Singleton
from dependency_injector.wiring import Provide, inject
from loguru import logger
from telegram.ext import Application as TelegramApp

from pdf_bot.containers import Application
from pdf_bot.log.log_handler import InterceptLoggingHandler
from pdf_bot.settings import Settings
from pdf_bot.telegram_dispatcher import TelegramDispatcher
from pdf_bot.telegram_handler import AbstractTelegramHandler


@inject
def main(
    telegram_app: TelegramApp,
    settings: Settings = Provide[
        Application.core.settings  # pylint: disable=no-member
    ],
    telegram_dispatcher: TelegramDispatcher = Provide[
        Application.telegram_bot.dispatcher  # pylint: disable=no-member
    ],
) -> None:
    logging.basicConfig(
        handlers=[InterceptLoggingHandler()], level=logging.INFO, force=True
    )

    if settings["sentry_dsn"] is not None:  # type: ignore
        sentry_sdk.init(settings["sentry_dsn"], traces_sample_rate=1.0)  # type: ignore
    else:
        logger.warning("SENTRY_DSN not set")

    telegram_dispatcher.setup(telegram_app)
    if settings["app_url"] is not None:  # type: ignore
        telegram_app.run_webhook(
            listen="0.0.0.0",
            port=settings["port"],  # type: ignore
            url_path=settings["telegram_token"],  # type: ignore
            webhook_url=f"{settings['app_url']}/{settings['telegram_token']}",  # type: ignore
        )
        logger.info("Bot started webhook")
    else:
        telegram_app.run_polling()
        logger.info("Bot started polling")


if __name__ == "__main__":
    app = Application()
    app.wire(modules=[__name__])

    _telegram_app = (
        TelegramApp.builder()
        .bot(app.core.telegram_bot())
        .concurrent_updates(True)
        .build()
    )

    # Dependency injectior only initialises the classes if they are referenced. Since
    # the processors are not referenced anywhere, we need to explicitly initialise them
    # so that they're registered under AbstractFileProcessor
    for provider in app.processors.providers.values():  # type: ignore
        if isinstance(provider, Singleton):
            provider()

    # Similarly, initialise and register all the handlers for the bot
    for provider in app.handlers.providers.values():  # type: ignore
        if isinstance(provider, Singleton):
            handler = provider()
            if isinstance(handler, AbstractTelegramHandler):
                _telegram_app.add_handlers(handler.handlers)

    main(_telegram_app)
