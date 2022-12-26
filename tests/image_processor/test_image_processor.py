import pytest
from telegram import InlineKeyboardMarkup

from pdf_bot.image_processor import BeautifyImageData, ImageProcessor, ImageToPdfData
from pdf_bot.models import TaskData
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramTestMixin


class TestImageProcessor(
    LanguageServiceTestMixin,
    TelegramTestMixin,
):
    TASKS = [
        TaskData("Beautify", "beautify_image", BeautifyImageData),
        TaskData("To PDF", "image_to_pdf", ImageToPdfData),
    ]

    def setup_method(self) -> None:
        super().setup_method()
        self.language_service = self.mock_language_service()
        self.sut = ImageProcessor(self.language_service)

    @pytest.mark.asyncio
    async def test_ask_image_task(self) -> None:
        actual = await self.sut.ask_image_task(
            self.telegram_update, self.telegram_context
        )
        assert actual == ImageProcessor.WAIT_IMAGE_TASK

        _args, kwargs = self.telegram_update.effective_message.reply_text.call_args
        reply_markup: InlineKeyboardMarkup | None = kwargs.get("reply_markup")
        assert reply_markup is not None

        index = 0
        for keyboard_list in reply_markup.inline_keyboard:
            for keyboard in keyboard_list:
                assert isinstance(keyboard.callback_data, self.TASKS[index].data_type)
                index += 1
            if index >= len(self.TASKS):
                break

        # Ensure that we've checked all tasks
        assert index == len(self.TASKS)
