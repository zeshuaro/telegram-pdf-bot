from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from typing import Generator

from telegram import Bot
from telegram.ext import Updater


class TelegramService:
    def __init__(self, updater: Updater | None = None, bot: Bot | None = None) -> None:
        self.bot = bot or updater.bot

    @contextmanager
    def download_file(self, file_id: str) -> Generator[str, None, None]:
        try:
            tf = NamedTemporaryFile()
            file = self.bot.get_file(file_id)
            file.download(custom_path=tf.name)
            yield tf.name
        finally:
            tf.close()
