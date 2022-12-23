import os

import sentry_sdk
from dotenv import load_dotenv
from telegram import MessageEntity, Update
from telegram.error import BadRequest, Unauthorized
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    PreCheckoutQueryHandler,
)
from telegram.ext.dispatcher import Dispatcher

from pdf_bot.command.command_service import CommandService
from pdf_bot.compare import CompareHandlers
from pdf_bot.consts import LANGUAGES, PAYMENT, SET_LANG
from pdf_bot.feedback import FeedbackHandler
from pdf_bot.file import FileHandlers
from pdf_bot.image_handler import BatchImageHandler
from pdf_bot.language import LanguageService
from pdf_bot.merge import MergeHandlers
from pdf_bot.payment import PaymentService
from pdf_bot.text import TextHandlers
from pdf_bot.watermark import WatermarkHandlers
from pdf_bot.webpage import WebpageHandler

load_dotenv()


class TelegramDispatcher:
    _CALLBACK_DATA = "callback_data"

    def __init__(
        self,
        command_service: CommandService,
        compare_handlers: CompareHandlers,
        feedback_handler: FeedbackHandler,
        file_handlers: FileHandlers,
        image_handler: BatchImageHandler,
        language_service: LanguageService,
        merge_handlers: MergeHandlers,
        payment_service: PaymentService,
        text_handlers: TextHandlers,
        watermark_handlers: WatermarkHandlers,
        webpage_handler: WebpageHandler,
    ) -> None:
        self.command_service = command_service
        self.compare_handlers = compare_handlers
        self.feedback_handler = feedback_handler
        self.file_handlers = file_handlers
        self.image_handler = image_handler
        self.language_service = language_service
        self.merge_handlers = merge_handlers
        self.payment_service = payment_service
        self.text_handlers = text_handlers
        self.watermark_handlers = watermark_handlers
        self.webpage_handler = webpage_handler

    def setup(self, dispatcher: Dispatcher) -> None:
        dispatcher.add_handler(
            CommandHandler(
                "start",
                self.payment_service.send_support_options,
                Filters.regex("support"),
                run_async=True,
            )
        )
        dispatcher.add_handler(
            CommandHandler(
                "start", self.command_service.send_start_message, run_async=True
            )
        )

        dispatcher.add_handler(
            CommandHandler(
                "help", self.command_service.send_help_message, run_async=True
            )
        )
        dispatcher.add_handler(
            CommandHandler(
                "setlang", self.language_service.send_language_options, run_async=True
            )
        )
        dispatcher.add_handler(
            CommandHandler(
                "support", self.payment_service.send_support_options, run_async=True
            )
        )

        # Callback query handler
        dispatcher.add_handler(
            CallbackQueryHandler(self.process_callback_query, run_async=True)
        )

        # Payment handlers
        dispatcher.add_handler(
            PreCheckoutQueryHandler(
                self.payment_service.precheckout_check, run_async=True
            )
        )
        dispatcher.add_handler(
            MessageHandler(
                Filters.successful_payment,
                self.payment_service.successful_payment,
                run_async=True,
            )
        )

        # URL handler
        dispatcher.add_handler(
            MessageHandler(
                Filters.entity(MessageEntity.URL),
                self.webpage_handler.url_to_pdf,
                run_async=True,
            )
        )

        # PDF commands handlers
        dispatcher.add_handler(self.compare_handlers.conversation_handler())
        dispatcher.add_handler(self.merge_handlers.conversation_handler())
        dispatcher.add_handler(self.image_handler.conversation_handler())
        dispatcher.add_handler(self.text_handlers.conversation_handler())
        dispatcher.add_handler(self.watermark_handlers.conversation_handler())

        # PDF file handler
        dispatcher.add_handler(self.file_handlers.conversation_handler())

        # Feedback handler
        dispatcher.add_handler(self.feedback_handler.conversation_handler())

        # Admin commands handlers
        ADMIN_TELEGRAM_ID = os.environ.get("ADMIN_TELEGRAM_ID")
        if ADMIN_TELEGRAM_ID is not None:
            dispatcher.add_handler(
                CommandHandler(
                    "send",
                    self.command_service.send_message_to_user,
                    Filters.user(int(ADMIN_TELEGRAM_ID)),
                )
            )

        # Log all errors
        dispatcher.add_error_handler(self.error_callback)  # type: ignore

    def process_callback_query(
        self,
        update: Update,
        context: CallbackContext,
    ) -> None:
        _ = self.language_service.set_app_language(update, context)
        query = update.callback_query
        data = query.data

        if self._CALLBACK_DATA not in context.user_data:  # type: ignore
            context.user_data[self._CALLBACK_DATA] = set()  # type: ignore

        if data not in context.user_data[self._CALLBACK_DATA]:  # type: ignore
            context.user_data[self._CALLBACK_DATA].add(data)  # type: ignore
            if data == SET_LANG:
                self.language_service.send_language_options(update, context)
            elif data in LANGUAGES:
                self.language_service.update_user_language(update, context, query)
            elif data == PAYMENT:
                self.payment_service.send_support_options(update, context, query)
            elif data.startswith("payment,"):
                self.payment_service.send_invoice(update, context, query)

            context.user_data[self._CALLBACK_DATA].remove(data)  # type: ignore

        try:
            query.answer()
        except BadRequest as e:
            if e.message.startswith("Query is too old"):
                context.bot.send_message(
                    query.from_user.id,
                    _(
                        "The button has expired, please try again with a new"
                        " message/query then press the new button"
                    ),
                )
            else:
                raise

    def error_callback(self, update: Update, context: CallbackContext) -> None:
        try:
            if context.error is not None:
                raise context.error
        except Unauthorized:
            pass
        except Exception as e:  # pylint: disable=broad-except
            _ = self.language_service.set_app_language(update, context)
            update.effective_message.reply_text(  # type: ignore
                _("Something went wrong, please try again")
            )
            sentry_sdk.capture_exception(e)
