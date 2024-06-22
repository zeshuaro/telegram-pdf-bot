from contextlib import suppress
from gettext import gettext as _

import sentry_sdk
from loguru import logger
from telegram import Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from pdf_bot.language import LanguageService


class ErrorHandler:
    def __init__(self, language_service: LanguageService) -> None:
        self.language_service = language_service

    async def callback(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        if context.error is None:
            return

        if not isinstance(update, Update):
            logger.exception(
                "Something went wrong without an Update instance", exc_info=context.error
            )
            sentry_sdk.capture_exception(context.error)
            return

        await self._handle_error(update, context)

    async def _handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            raise context.error  # type: ignore[misc] # noqa: TRY301
        except Forbidden:
            pass
        except BadRequest as e:
            await self._handle_bad_request(update, context, e)
        except Exception as e:  # noqa: BLE001
            await self._send_message(update, context, _("Something went wrong, please try again"))
            sentry_sdk.capture_exception(e)

    async def _handle_bad_request(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, error: BadRequest
    ) -> None:
        err_text = _("Something went wrong, please try again")
        err_msg = error.message.lower()

        if err_msg.startswith(
            (
                "message is not modified",
                "need administrator rights",
                "message to delete not found",
                "message to edit not found",
            )
        ):
            return

        if err_msg.startswith("query is too old and response timeout expired"):
            err_text = _("The button has expired, start over with your file or command")
        elif err_msg.startswith("photo_invalid_dimensions"):
            err_text = _("The resulted image is invalid, try again")
        elif not err_msg.startswith("file must be non-empty"):
            sentry_sdk.capture_exception(error)

        await self._send_message(update, context, err_text)

    async def _send_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
    ) -> None:
        chat_id = None
        if update.effective_message is not None:
            chat_id = update.effective_message.chat_id
        elif update.effective_chat is not None:
            chat_id = update.effective_chat.id

        if chat_id is None:
            return

        with suppress(Exception):
            _ = self.language_service.set_app_language(update, context)
            await context.bot.send_message(chat_id, _(text))
