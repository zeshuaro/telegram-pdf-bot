from unittest.mock import MagicMock

import pytest
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters

from pdf_bot.compare import CompareHandler, CompareService
from pdf_bot.consts import TEXT_FILTER
from tests.telegram_internal import TelegramServiceTestMixin


class TestCompareHandlers(TelegramServiceTestMixin):
    COMPARE_COMMAND = "compare"
    CANCEL_COMMAND = "cancel"

    def setup_method(self) -> None:
        super().setup_method()
        self.compare_service = MagicMock(spec=CompareService)
        self.telegram_service = self.mock_telegram_service()

        self.sut = CompareHandler(self.compare_service, self.telegram_service)

    @pytest.mark.asyncio
    async def test_handlers(self) -> None:
        actual = self.sut.handlers
        assert len(actual) == 1

        handler = actual[0]
        assert isinstance(handler, ConversationHandler)

        entry_points = handler.entry_points
        assert len(entry_points) == 1
        assert isinstance(entry_points[0], CommandHandler)
        assert entry_points[0].commands == {self.COMPARE_COMMAND}

        states = handler.states
        assert CompareService.WAIT_FIRST_PDF in states
        wait_first_pdf = states[CompareService.WAIT_FIRST_PDF]
        assert len(wait_first_pdf) == 1
        assert isinstance(wait_first_pdf[0], MessageHandler)
        assert wait_first_pdf[0].filters == filters.Document.PDF

        assert CompareService.WAIT_SECOND_PDF in states
        wait_second_pdf = states[CompareService.WAIT_SECOND_PDF]
        assert len(wait_second_pdf) == 1
        assert isinstance(wait_second_pdf[0], MessageHandler)
        assert wait_second_pdf[0].filters == filters.Document.PDF

        fallbacks = handler.fallbacks
        assert len(fallbacks) == 2

        assert isinstance(fallbacks[0], CommandHandler)
        assert fallbacks[0].commands == {self.CANCEL_COMMAND}

        assert isinstance(fallbacks[1], MessageHandler)
        assert fallbacks[1].filters.name == TEXT_FILTER.name

        for handler in entry_points + wait_first_pdf + wait_second_pdf + fallbacks:
            await handler.callback(self.telegram_update, self.telegram_context)

        self.compare_service.ask_first_pdf.assert_called_once()
        self.compare_service.check_first_pdf.assert_called_once()
        self.compare_service.compare_pdfs.assert_called_once()
        self.compare_service.check_text.assert_called_once()
        self.telegram_service.cancel_conversation.assert_called_once()
