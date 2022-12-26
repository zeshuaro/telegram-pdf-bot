from typing import Type
from unittest.mock import MagicMock

import pytest
from telegram import InlineKeyboardMarkup

from pdf_bot.file_processor import AbstractFileProcessor, AbstractFileTaskProcessor
from pdf_bot.models import FileData, TaskData
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramTestMixin


class MockProcessor(AbstractFileTaskProcessor):
    TASK_DATA_LIST = [TaskData("a", FileData), TaskData("b", FileData)]

    @property
    def processor_type(self) -> Type[AbstractFileProcessor]:
        mock_type = MagicMock(spec=AbstractFileProcessor)
        mock_type.get_task_data_list.return_value = self.TASK_DATA_LIST
        return mock_type


class TestAbstractFileTaskProcessor(LanguageServiceTestMixin, TelegramTestMixin):
    WAIT_FILE_TASK = "wait_file_task"

    def setup_method(self) -> None:
        super().setup_method()
        self.language_service = self.mock_language_service()
        self.sut = MockProcessor(self.language_service)

    @pytest.mark.asyncio
    async def test_ask_task(self) -> None:
        tasks = MockProcessor.TASK_DATA_LIST

        actual = await self.sut.ask_task(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_FILE_TASK
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
