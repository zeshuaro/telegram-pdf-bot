import hashlib
from contextlib import suppress
from urllib.parse import urlparse

from telegram import Message, Update
from telegram.ext import ContextTypes
from weasyprint import HTML
from weasyprint.css.utils import InvalidValues
from weasyprint.urls import URLFetchingError

from pdf_bot.analytics import TaskType
from pdf_bot.io import IOService
from pdf_bot.language import LanguageService
from pdf_bot.telegram_internal import (
    TelegramGetUserDataError,
    TelegramService,
    TelegramUpdateUserDataError,
)


class WebpageService:
    def __init__(
        self,
        io_service: IOService,
        language_service: LanguageService,
        telegram_service: TelegramService,
    ) -> None:
        self.io_service = io_service
        self.language_service = language_service
        self.telegram_service = telegram_service

    async def url_to_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.effective_message  # type: ignore
        url = message.text
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()

        if self.telegram_service.user_data_contains(context, url_hash):
            await message.reply_text(
                _("You've sent me this webpage already and I'm still converting it")
            )
            return

        await message.reply_text(_("Converting your webpage into a PDF file"))
        self._cache_url(context, url_hash)
        await self._url_to_pdf(update, context, url)
        self._clear_url_cache(context, url_hash)

    def _cache_url(self, context: ContextTypes.DEFAULT_TYPE, url_hash: str) -> None:
        with suppress(TelegramUpdateUserDataError):
            self.telegram_service.update_user_data(context, url_hash, None)

    def _clear_url_cache(self, context: ContextTypes.DEFAULT_TYPE, url_hash: str) -> None:
        with suppress(TelegramGetUserDataError):
            self.telegram_service.get_user_data(context, url_hash)

    async def _url_to_pdf(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, url: str
    ) -> None:
        _ = self.language_service.set_app_language(update, context)
        o = urlparse(url)
        err_text = None

        with self.io_service.create_temp_pdf_file(o.hostname) as out_path:
            try:
                HTML(url=url).write_pdf(out_path)
                await self.telegram_service.send_file(
                    update, context, out_path, TaskType.url_to_pdf
                )
            except URLFetchingError:
                err_text = _("Unable to reach your webpage")
            except (
                AssertionError,
                AttributeError,
                IndexError,
                InvalidValues,
                KeyError,
                OverflowError,
                RuntimeError,
                ValueError,
                TypeError,
            ):
                err_text = _("Failed to convert your webpage")

        if err_text is not None:
            await update.effective_message.reply_text(err_text)  # type: ignore
