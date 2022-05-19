from typing import cast
from unittest.mock import MagicMock, call, patch

import pytest

from pdf_bot.compare import CompareService
from pdf_bot.pdf import PdfService
from pdf_bot.telegram import TelegramService


@pytest.fixture(name="telegram_service")
def fixture_telegram_service() -> TelegramService:
    service = cast(TelegramService, MagicMock())
    service.download_file.__enter__ = MagicMock()
    return service


@pytest.fixture(name="pdf_service")
def fixture_pdf_service(telegram_service: TelegramService) -> CompareService:
    return PdfService(telegram_service)


def test_compare_pdfs(
    pdf_service: PdfService, telegram_service: TelegramService, document_id: str
):
    with patch(
        "pdf_bot.pdf.pdf_service.pdf_diff"
    ) as pdf_diff, pdf_service.compare_pdfs(document_id, document_id):
        assert pdf_diff.main.called
        calls = [call(document_id) for _ in range(2)]
        telegram_service.download_file.assert_has_calls(calls, any_order=True)
