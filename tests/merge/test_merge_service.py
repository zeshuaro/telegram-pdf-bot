from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from pdf_bot.merge import MergeService
from pdf_bot.models import FileData
from pdf_bot.pdf import PdfService
from pdf_bot.telegram import TelegramService, TelegramServiceError

WAIT_MERGE_PDF = 0
MERGE_PDF_DATA = "merge_pdf_data"


@pytest.fixture(name="merge_service")
def fixture_merge_service(pdf_service: PdfService, telegram_service: TelegramService):
    return MergeService(pdf_service, telegram_service)


@pytest.fixture(scope="session", autouse=True)
def merge_service_set_lang() -> Iterator[None]:
    with patch("pdf_bot.merge.merge_service.set_lang"):
        yield


@pytest.fixture(scope="session", autouse=True)
def utils_set_lang() -> Iterator[None]:
    with patch("pdf_bot.utils.set_lang"):
        yield


def test_ask_first_pdf(
    merge_service: MergeService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    actual = merge_service.ask_first_pdf(telegram_update, telegram_context)
    assert actual == WAIT_MERGE_PDF
    telegram_context.user_data.__setitem__.assert_called_with(MERGE_PDF_DATA, [])


def test_check_pdf(
    merge_service: MergeService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
    file_data: FileData,
):
    file_data_list = MagicMock()
    telegram_context.user_data.__getitem__.return_value = file_data_list

    actual = merge_service.check_pdf(telegram_update, telegram_context)

    assert actual == WAIT_MERGE_PDF
    telegram_context.user_data.__getitem__.assert_called_with(MERGE_PDF_DATA)
    file_data_list.append.assert_called_once_with(file_data)
    telegram_service.send_file_names.assert_called_once()


def test_check_pdf_invlid_pdf(
    merge_service: MergeService,
    telegram_service: TelegramService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    telegram_service.check_pdf_document.side_effect = TelegramServiceError()

    actual = merge_service.check_pdf(telegram_update, telegram_context)

    assert actual == WAIT_MERGE_PDF
    telegram_context.user_data.__getitem__.assert_not_called()
    telegram_service.send_file_names.assert_not_called()
