from gettext import gettext as _

import sentry_sdk
from telegram import MessageEntity, Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from pdf_bot.file_handler import FileHandler
from pdf_bot.language import LanguageService
from pdf_bot.webpage import WebpageHandler


class TelegramDispatcher:
    _CALLBACK_DATA = "callback_data"

    def __init__(
        self,
        file_handlers: FileHandler,
        language_service: LanguageService,
        webpage_handler: WebpageHandler,
    ) -> None:
        self.file_handlers = file_handlers
        self.language_service = language_service
        self.webpage_handler = webpage_handler

    def setup(self, telegram_app: Application) -> None:
        # URL handler
        telegram_app.add_handler(
            MessageHandler(
                filters.Entity(MessageEntity.URL), self.webpage_handler.url_to_pdf
            )
        )

        # PDF file handler
        telegram_app.add_handler(self.file_handlers.conversation_handler())

        # Log all errors
        telegram_app.add_error_handler(self.error_callback)

    async def error_callback(
        self, update: object, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        err_text = _("Something went wrong, please try again")
        try:
            if context.error is not None:
                raise context.error
        except Forbidden:
            pass
        except BadRequest as e:
            err_msg = e.message.lower()
            if err_msg.startswith("message is not modified"):
                return
            if err_msg.startswith("query is too old and response timeout expired"):
                err_text = _(
                    "The button has expired, start over with your file or command"
                )
            else:
                sentry_sdk.capture_exception(e)

            await self._send_message(update, context, err_text)
        except Exception as e:  # pylint: disable=broad-except
            await self._send_message(update, context, err_text)
            sentry_sdk.capture_exception(e)

    async def _send_message(
        self, update: object, context: ContextTypes.DEFAULT_TYPE, text: str
    ) -> None:
        if not isinstance(update, Update):
            return

        chat_id = None
        if update.effective_message is not None:
            chat_id = update.effective_message.chat_id
        elif update.effective_chat is not None:
            chat_id = update.effective_chat.id

        if chat_id is None:
            return

        try:
            _ = self.language_service.set_app_language(update, context)
            await context.bot.send_message(chat_id, _(text))
        except Exception:  # pylint: disable=broad-except
            pass
