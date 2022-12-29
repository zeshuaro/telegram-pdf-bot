import logging

from telegram import Message, Update
from telegram.ext import ContextTypes

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

    async def url_to_pdf(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        _ = self.language_service.set_app_language(update, context)
        message: Message = update.effective_message  # type: ignore
        url = message.text
        user_data = context.user_data

        if (
            user_data is not None
            and self.URLS in user_data
            and url in user_data[self.URLS]
        ):
            await message.reply_text(
                _("You've sent me this web page already and I'm still converting it")
            )
            return

        await message.reply_text(_("Converting your web page into a PDF file"))
        if self.URLS in user_data:  # type: ignore
            user_data[self.URLS].add(url)  # type: ignore
        else:
            user_data[self.URLS] = {url}  # type: ignore

        try:
            with self.webpage_service.url_to_pdf(url) as out_path:
                await self.telegram_service.send_file(
                    update, context, out_path, TaskType.url_to_pdf
                )
        except WebpageServiceError as e:
            await message.reply_text(_(str(e)))

        user_data[self.URLS].remove(url)  # type: ignore
