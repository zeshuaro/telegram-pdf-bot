from unittest.mock import MagicMock

import pytest
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters

from pdf_bot.consts import TEXT_FILTER
from pdf_bot.image_handler import BatchImageHandler, BatchImageService
from tests.telegram_internal import TelegramServiceTestMixin


class TestCompareHandlers(TelegramServiceTestMixin):
    IMAGE_COMMAND = "image"
    CANCEL_COMMAND = "cancel"

    def setup_method(self) -> None:
        super().setup_method()
        self.image_service = MagicMock(spec=BatchImageService)
        self.telegram_service = self.mock_telegram_service()

        self.sut = BatchImageHandler(self.image_service, self.telegram_service)

    @pytest.mark.asyncio
    async def test_handlers(self) -> None:
        actual = self.sut.handlers
        assert len(actual) == 1

        handler = actual[0]
        assert isinstance(handler, ConversationHandler)

        entry_points = handler.entry_points
        assert len(entry_points) == 1
        assert isinstance(entry_points[0], CommandHandler)
        assert entry_points[0].commands == {self.IMAGE_COMMAND}

        states = handler.states
        assert BatchImageService.WAIT_IMAGE in states
        wait_image = states[BatchImageService.WAIT_IMAGE]
        assert len(wait_image) == 2

        assert isinstance(wait_image[0], MessageHandler)
        assert wait_image[0].filters.name == (filters.Document.IMAGE | filters.PHOTO).name

        assert isinstance(wait_image[1], MessageHandler)
        assert wait_image[1].filters.name == TEXT_FILTER.name

        fallbacks = handler.fallbacks
        assert len(fallbacks) == 1

        assert isinstance(fallbacks[0], CommandHandler)
        assert fallbacks[0].commands == {self.CANCEL_COMMAND}

        for handler in entry_points + wait_image + fallbacks:
            await handler.callback(self.telegram_update, self.telegram_context)

        self.image_service.ask_first_image.assert_called_once()
        self.image_service.check_image.assert_called_once()
        self.image_service.check_text.assert_called_once()
        self.telegram_service.cancel_conversation.assert_called_once()
