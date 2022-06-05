from typing import Iterator
from unittest.mock import patch

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from pdf_bot.file_task import FileTaskService, file_task_constants

PDF_INFO = "pdf_info"


@pytest.fixture(name="file_task_service")
def fixture_file_service() -> FileTaskService:
    return FileTaskService()


@pytest.fixture(scope="session", autouse=True)
def set_lang() -> Iterator[None]:
    with patch("pdf_bot.file_task.file_task_service.set_lang"):
        yield


def test_ask_pdf_task(
    file_task_service: FileTaskService,
    telegram_update: Update,
    telegram_context: CallbackContext,
):
    actual = file_task_service.ask_pdf_task(telegram_update, telegram_context)
    assert actual == file_task_constants.WAIT_PDF_TASK
