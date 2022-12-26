import pytest

from pdf_bot.file_task import FileTaskService
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramTestMixin


class TestFileTaskService(LanguageServiceTestMixin, TelegramTestMixin):
    WAIT_PDF_TASK = "wait_pdf_task"
    WAIT_IMAGE_TASK = "wait_image_task"

    def setup_method(self) -> None:
        super().setup_method()
        self.language_service = self.mock_language_service()
        self.sut = FileTaskService(self.language_service)

    @pytest.mark.asyncio
    async def test_ask_pdf_task(self) -> None:
        actual = await self.sut.ask_pdf_task(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_PDF_TASK
        self.telegram_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_image_task(self) -> None:
        actual = await self.sut.ask_image_task(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_IMAGE_TASK
        self.telegram_update.message.reply_text.assert_called_once()
