import os

import sentry_sdk
from dotenv import load_dotenv
from telegram import MessageEntity, Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

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

    def setup(self, telegram_app: Application) -> None:
        telegram_app.add_handler(
            CommandHandler(
                "start",
                self.payment_service.send_support_options,
                filters.Regex("support"),
            )
        )
        telegram_app.add_handler(
            CommandHandler("start", self.command_service.send_start_message)
        )

        telegram_app.add_handler(
            CommandHandler("help", self.command_service.send_help_message)
        )
        telegram_app.add_handler(
            CommandHandler("setlang", self.language_service.send_language_options)
        )
        telegram_app.add_handler(
            CommandHandler("support", self.payment_service.send_support_options)
        )

        # Payment handlers
        telegram_app.add_handler(
            PreCheckoutQueryHandler(self.payment_service.precheckout_check)
        )
        telegram_app.add_handler(
            MessageHandler(
                filters.SUCCESSFUL_PAYMENT, self.payment_service.successful_payment
            )
        )

        # URL handler
        telegram_app.add_handler(
            MessageHandler(
                filters.Entity(MessageEntity.URL), self.webpage_handler.url_to_pdf
            )
        )

        # PDF commands handlers
        telegram_app.add_handler(self.compare_handlers.conversation_handler())
        telegram_app.add_handler(self.merge_handlers.conversation_handler())
        telegram_app.add_handler(self.image_handler.conversation_handler())
        telegram_app.add_handler(self.text_handlers.conversation_handler())
        telegram_app.add_handler(self.watermark_handlers.conversation_handler())

        # PDF file handler
        telegram_app.add_handler(self.file_handlers.conversation_handler())

        # Feedback handler
        telegram_app.add_handler(self.feedback_handler.conversation_handler())

        # Callback query handler
        telegram_app.add_handler(CallbackQueryHandler(self.process_callback_query))

        # Admin commands handlers
        ADMIN_TELEGRAM_ID = os.environ.get("ADMIN_TELEGRAM_ID")
        if ADMIN_TELEGRAM_ID is not None:
            telegram_app.add_handler(
                CommandHandler(
                    "send",
                    self.command_service.send_message_to_user,
                    filters.User(int(ADMIN_TELEGRAM_ID)),
                )
            )

        # Log all errors
        telegram_app.add_error_handler(self.error_callback)

    async def process_callback_query(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        _ = self.language_service.set_app_language(update, context)
        query = update.callback_query
        data = query.data

        if isinstance(data, str):
            if data == SET_LANG:
                await self.language_service.send_language_options(update, context)
            elif data in LANGUAGES:
                await self.language_service.update_user_language(update, context, query)
            elif data == PAYMENT:
                await self.payment_service.send_support_options(update, context, query)
            elif data.startswith("payment,"):
                await self.payment_service.send_invoice(update, context, query)

            try:
                await query.answer()
            except BadRequest as e:
                if e.message.startswith("Query is too old"):
                    await context.bot.send_message(
                        query.from_user.id,
                        _(
                            "The button has expired, please try again with a new"
                            " message/query then press the new button"
                        ),
                    )
                else:
                    raise

    async def error_callback(
        self, update: object, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        try:
            if context.error is not None:
                raise context.error
        except Forbidden:
            pass
        except Exception as e:  # pylint: disable=broad-except
            if isinstance(update, Update):
                _ = self.language_service.set_app_language(update, context)
                chat_id = None

                if update.effective_message is not None:
                    chat_id = update.effective_message.chat_id
                elif update.effective_chat is not None:
                    chat_id = update.effective_chat.id
                if chat_id is not None:
                    await context.bot.send_message(
                        chat_id,
                        _("Something went wrong, please try again"),
                    )
            sentry_sdk.capture_exception(e)
