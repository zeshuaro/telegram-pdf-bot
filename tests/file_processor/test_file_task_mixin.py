import pytest
from telegram import InlineKeyboardMarkup
from telegram.ext import ConversationHandler

from pdf_bot.consts import GENERIC_ERROR
from pdf_bot.file_processor import FileTaskMixin
from pdf_bot.models import FileData, TaskData
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramTestMixin


class TestFileTaskMixin(LanguageServiceTestMixin, TelegramTestMixin):
    WAIT_FILE_TASK = "wait_file_task"
    TASK_DATA_LIST = [TaskData("a", FileData), TaskData("b", FileData)]

    def setup_method(self) -> None:
        super().setup_method()
        self.language_service = self.mock_language_service()
        self.sut = FileTaskMixin()

    @pytest.mark.asyncio
    async def test_ask_task_helper(self) -> None:
        actual = await self.sut.ask_task_helper(
            self.language_service,
            self.telegram_update,
            self.telegram_context,
            self.TASK_DATA_LIST,
        )

        assert actual == self.WAIT_FILE_TASK
        self._assert_inline_keyboard()

    @pytest.mark.asyncio
    async def test_ask_task_helper_without_user_data(self) -> None:
        self.telegram_context.user_data = None

        actual = await self.sut.ask_task_helper(
            self.language_service,
            self.telegram_update,
            self.telegram_context,
            self.TASK_DATA_LIST,
        )

        assert actual == self.WAIT_FILE_TASK
        self._assert_inline_keyboard()

    @pytest.mark.asyncio
    async def test_ask_task_helper_without_file_data_and_file(self) -> None:
        self.telegram_context.user_data = (
            self.telegram_message.document
        ) = self.telegram_message.photo = None

        actual = await self.sut.ask_task_helper(
            self.language_service,
            self.telegram_update,
            self.telegram_context,
            self.TASK_DATA_LIST,
        )

        assert actual == ConversationHandler.END
        self.telegram_update.effective_message.reply_text.assert_called_once_with(GENERIC_ERROR)

    def _assert_inline_keyboard(self) -> None:
        tasks = self.TASK_DATA_LIST
        _args, kwargs = self.telegram_update.effective_message.reply_text.call_args

        reply_markup: InlineKeyboardMarkup | None = kwargs.get("reply_markup")
        assert reply_markup is not None

        index = 0
        for keyboard_list in reply_markup.inline_keyboard:
            for keyboard in keyboard_list:
                assert keyboard.text == tasks[index].label
                assert isinstance(keyboard.callback_data, tasks[index].data_type)
                index += 1
            if index >= len(tasks):
                break

        # Ensure that we've checked all tasks
        assert index == len(tasks)
