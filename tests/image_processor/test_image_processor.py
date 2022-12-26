import pytest

from pdf_bot.image_processor import ImageProcessor
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramTestMixin


class TestImageProcessor(
    LanguageServiceTestMixin,
    TelegramTestMixin,
):
    WAIT_FILE_TASK = "wait_file_task"

    def setup_method(self) -> None:
        super().setup_method()
        self.language_service = self.mock_language_service()
        self.sut = ImageProcessor(self.language_service)

    @pytest.mark.asyncio
    async def test_ask_image_task(self) -> None:
        actual = await self.sut.ask_image_task(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_FILE_TASK
        self.telegram_update.effective_message.reply_text.assert_called_once()
