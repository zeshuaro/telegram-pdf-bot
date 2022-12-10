import logging

from telegram import Update
from telegram.ext import CallbackContext

from pdf_bot.analytics import TaskType
from pdf_bot.language import LanguageService
from pdf_bot.telegram_internal import TelegramService

from .exceptions import WebpageServiceError
from .webpage_service import WebpageService

logging.getLogger("weasyprint").setLevel(100)


class WebpageHandler:
    URLS = "urls"

    def __init__(
        self,
        webpage_service: WebpageService,
        language_service: LanguageService,
        telegram_service: TelegramService,
    ) -> None:
        self.webpage_service = webpage_service
        self.language_service = language_service
        self.telegram_service = telegram_service

    def url_to_pdf(self, update: Update, context: CallbackContext) -> None:
        _ = self.language_service.set_app_language(update, context)
        message = update.effective_message
        url = message.text
        user_data = context.user_data

        if (
            user_data is not None
            and self.URLS in user_data
            and url in user_data[self.URLS]
        ):
            message.reply_text(
                _("You've sent me this web page already and I'm still converting it")
            )
            return

        message.reply_text(_("Converting your web page into a PDF file"))
        if self.URLS in user_data:
            user_data[self.URLS].add(url)
        else:
            user_data[self.URLS] = {url}

        try:
            with self.webpage_service.url_to_pdf(url) as out_path:
                self.telegram_service.reply_with_file(
                    update, context, out_path, TaskType.url_to_pdf
                )
        except WebpageServiceError as e:
            message.reply_text(_(str(e)))

        user_data[self.URLS].remove(url)
