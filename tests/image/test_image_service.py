from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest
from telegram import Document, Update
from telegram.ext import CallbackContext

from pdf_bot.image import ImageService
from pdf_bot.models import FileData
from pdf_bot.pdf import PdfService
from pdf_bot.telegram import TelegramService, TelegramServiceError

WAIT_IMAGE = 0
IMAGE_DATA = "image_data"


@pytest.fixture(name="image_service")
def fixture_image_service(pdf_service: PdfService, telegram_service: TelegramService):
    return ImageService(pdf_service, telegram_service)


@pytest.fixture(scope="session", autouse=True)
def image_service_set_lang() -> Iterator[None]:
    with patch("pdf_bot.image.image_service.set_lang"):
        yield


@pytest.fixture(scope="session", autouse=True)
def utils_set_lang() -> Iterator[None]:
    with patch("pdf_bot.utils.set_lang"):
        yield


def test_ask_first_pdf(
    image_service: ImageService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    actual = image_service.ask_first_image(telegram_update, telegram_context)
    assert actual == WAIT_IMAGE
    telegram_context.user_data.__setitem__.assert_called_with(IMAGE_DATA, [])


def test_check_image(
    image_service: ImageService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    telegram_document: Document,
    file_data: FileData,
):
    file_data_list = MagicMock()
    telegram_context.user_data.__getitem__.return_value = file_data_list
    telegram_service.check_image.return_value = telegram_document

    actual = image_service.check_image(telegram_update, telegram_context)

    assert actual == WAIT_IMAGE
    telegram_context.user_data.__getitem__.assert_called_with(IMAGE_DATA)
    file_data_list.append.assert_called_once_with(file_data)
    telegram_service.send_file_names.assert_called_once()


def test_check_image_invlid_image(
    image_service: ImageService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    telegram_service.check_image.side_effect = TelegramServiceError()

    actual = image_service.check_image(telegram_update, telegram_context)

    assert actual == WAIT_IMAGE
    telegram_context.user_data.__getitem__.assert_not_called()
    telegram_service.send_file_names.assert_not_called()
