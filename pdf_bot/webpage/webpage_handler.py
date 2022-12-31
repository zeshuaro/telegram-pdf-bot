from telegram import MessageEntity
from telegram.ext import BaseHandler, MessageHandler, filters

from pdf_bot.telegram_handler import AbstractTelegramHandler

from .webpage_service import WebpageService


class WebpageHandler(AbstractTelegramHandler):
    def __init__(self, webpage_service: WebpageService) -> None:
        self.webpage_service = webpage_service

    @property
    def handlers(self) -> list[BaseHandler]:
        return [MessageHandler(filters.Entity(MessageEntity.URL), self.webpage_service.url_to_pdf)]
