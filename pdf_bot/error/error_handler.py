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
            try:
                raise context.error
            except Exception as e:  # pylint: disable=broad-except
                logger.exception("Something went wrong without an Update instance")
                sentry_sdk.capture_exception(e)
            return

        await self._handle_error(update, context)

    async def _handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            raise context.error  # type: ignore
        except Forbidden:
            pass
        except BadRequest as e:
            await self._handle_bad_request(update, context, e)
        except Exception as e:  # pylint: disable=broad-except
            await self._send_message(update, context, _("Something went wrong, please try again"))
            sentry_sdk.capture_exception(e)

    async def _handle_bad_request(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, error: BadRequest
    ) -> None:
        err_text = _("Something went wrong, please try again")
        err_msg = error.message.lower()

        if (
            err_msg.startswith("message is not modified")
            or err_msg.startswith("need administrator rights")
            or err_msg.startswith("message to delete not found")
            or err_msg.startswith("message to edit not found")
        ):
            return
        if err_msg.startswith("query is too old and response timeout expired"):
            err_text = _("The button has expired, start over with your file or command")
        else:
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

        try:
            _ = self.language_service.set_app_language(update, context)
            await context.bot.send_message(chat_id, _(text))
        except Exception:  # pylint: disable=broad-except
            pass
