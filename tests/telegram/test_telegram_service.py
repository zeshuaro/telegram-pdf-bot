import pytest
from telegram import Bot, File

from pdf_bot.telegram import TelegramService


@pytest.fixture(name="telegram_service")
def fixture_telegram_service(telegram_bot: Bot) -> TelegramService:
    return TelegramService(bot=telegram_bot)


def test_download_file(
    telegram_service: TelegramService,
    telegram_bot: Bot,
    telegram_file: File,
    document_id: str,
):
    telegram_bot.get_file.return_value = telegram_file
    with telegram_service.download_file(document_id):
        telegram_bot.get_file.assert_called_with(document_id)
        telegram_file.download.assert_called()
