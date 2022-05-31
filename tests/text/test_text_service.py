from typing import Iterator, cast
from unittest.mock import MagicMock, patch

import pytest
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.pdf import PdfService
from pdf_bot.telegram import TelegramService, TelegramUserDataKeyError
from pdf_bot.text import TextRepository, TextService

WAIT_TEXT = 0
WAIT_FONT = 1


@pytest.fixture(name="text_repository")
def fixture_text_repository() -> TextRepository:
    return cast(TextRepository, MagicMock())


@pytest.fixture(name="text_service")
def fixture_text_service(
    text_repository: TextRepository,
    pdf_service: PdfService,
    telegram_service: TelegramService,
) -> TextService:
    return TextService(text_repository, pdf_service, telegram_service)


@pytest.fixture(scope="session", autouse=True)
def set_lang() -> Iterator[None]:
    with patch("pdf_bot.text.text_service.set_lang"):
        yield


def test_ask_pdf_text(
    text_service: TextService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    actual = text_service.ask_pdf_text(telegram_update, telegram_context)
    assert actual == WAIT_TEXT


def test_ask_pdf_font(
    text_service: TextService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    actual = text_service.ask_pdf_font(telegram_update, telegram_context)
    assert actual == WAIT_FONT


def test_check_text(
    text_service: TextService,
    pdf_service: PdfService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    out_path = "out_path"
    pdf_service.create_pdf_from_text.return_value.__enter__.return_value = out_path

    with patch("pdf_bot.text.text_service.send_result_file") as send_result_file:
        actual = text_service.check_text(telegram_update, telegram_context)
        assert actual == ConversationHandler.END
        send_result_file.assert_called_once_with(
            telegram_update, telegram_context, out_path, TaskType.text_to_pdf
        )


def test_check_text_invalid_user_data(
    text_service: TextService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    telegram_service.get_user_data.side_effect = TelegramUserDataKeyError()
    with patch("pdf_bot.text.text_service.send_result_file") as send_result_file:
        actual = text_service.check_text(telegram_update, telegram_context)
        assert actual == ConversationHandler.END
        send_result_file.assert_not_called()


def test_check_text_unknown_font(
    text_service: TextService,
    text_repository: TextRepository,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    text_repository.get_font.return_value = None
    with patch("pdf_bot.text.text_service.send_result_file") as send_result_file:
        actual = text_service.check_text(telegram_update, telegram_context)
        assert actual == WAIT_FONT
        send_result_file.assert_not_called()
