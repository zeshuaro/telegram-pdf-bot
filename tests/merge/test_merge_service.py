from unittest.mock import MagicMock

import pytest
from telegram.ext import ConversationHandler

from pdf_bot.analytics import TaskType
from pdf_bot.merge import MergeService
from pdf_bot.models import FileData
from pdf_bot.pdf import PdfService, PdfServiceError
from pdf_bot.telegram_internal import TelegramServiceError
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestMergeService(
    LanguageServiceTestMixin,
    TelegramServiceTestMixin,
    TelegramTestMixin,
):
    WAIT_MERGE_PDF = 0
    MERGE_PDF_DATA = "merge_pdf_data"

    REMOVE_LAST_FILE = "Remove last file"
    DONE = "Done"
    CANCEL = "Cancel"

    def setup_method(self) -> None:
        super().setup_method()
        self.file_data_list = MagicMock(spec=list[FileData])

        self.pdf_service = MagicMock(spec=PdfService)
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()
        self.telegram_service.get_user_data.side_effect = None

        self.sut = MergeService(
            self.pdf_service,
            self.telegram_service,
            self.language_service,
        )

    @pytest.mark.asyncio
    async def test_ask_first_pdf(self) -> None:
        actual = await self.sut.ask_first_pdf(
            self.telegram_update, self.telegram_context
        )

        assert actual == self.WAIT_MERGE_PDF
        self._assert_ask_first_pdf()

    @pytest.mark.asyncio
    async def test_check_pdf(self) -> None:
        self.telegram_context.user_data.__getitem__.return_value = self.file_data_list

        actual = await self.sut.check_pdf(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_MERGE_PDF

        file_data = self.file_data_list.append.call_args.args[0]
        assert file_data == FileData(
            self.TELEGRAM_DOCUMENT_ID, self.TELEGRAM_DOCUMENT_NAME
        )

        self.telegram_service.send_file_names.assert_called_once()
        self.telegram_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_pdf_invlid_pdf(self) -> None:
        self.telegram_service.check_pdf_document.side_effect = TelegramServiceError()

        actual = await self.sut.check_pdf(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_MERGE_PDF
        self.telegram_context.user_data.__getitem__.assert_not_called()
        self.telegram_service.send_file_names.assert_not_called()
        self.telegram_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_text_remove_last(self) -> None:
        self.telegram_message.text = self.REMOVE_LAST_FILE
        self.telegram_service.get_user_data.return_value = self.file_data_list

        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_MERGE_PDF
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, self.MERGE_PDF_DATA
        )
        self.file_data_list.pop.assert_called_once()
        self.telegram_update.effective_message.reply_text.assert_called_once()
        self._assert_ask_first_pdf()

    @pytest.mark.asyncio
    async def test_check_text_remove_last_with_existing_file(self) -> None:
        self.telegram_message.text = self.REMOVE_LAST_FILE
        self.file_data_list.__len__.return_value = 1
        self.telegram_service.get_user_data.return_value = self.file_data_list

        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_MERGE_PDF
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, self.MERGE_PDF_DATA
        )
        self.file_data_list.pop.assert_called_once()
        assert self.telegram_update.effective_message.reply_text.call_count == 2
        self.telegram_context.user_data.__setitem__.assert_called_with(
            self.MERGE_PDF_DATA, self.file_data_list
        )
        self.telegram_service.send_file_names.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_text_remove_last_remove_error(self) -> None:
        self.telegram_message.text = self.REMOVE_LAST_FILE
        self.file_data_list.pop.side_effect = IndexError()
        self.telegram_service.get_user_data.return_value = self.file_data_list

        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_MERGE_PDF
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, self.MERGE_PDF_DATA
        )
        self.file_data_list.pop.assert_called_once()
        self.telegram_update.effective_message.reply_text.assert_called_once()
        self._assert_ask_first_pdf()

    @pytest.mark.asyncio
    async def test_check_text_done_and_merge(self) -> None:
        self.telegram_message.text = self.DONE
        self.file_data_list.__len__.return_value = 2
        self.telegram_service.get_user_data.return_value = self.file_data_list
        self.pdf_service.merge_pdfs.return_value.__aenter__.return_value = (
            self.FILE_PATH
        )

        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, self.MERGE_PDF_DATA
        )
        self.pdf_service.merge_pdfs.assert_called_once_with(self.file_data_list)
        self.telegram_service.send_file.assert_called_once_with(
            self.telegram_update,
            self.telegram_context,
            self.FILE_PATH,
            TaskType.merge_pdf,
        )

    @pytest.mark.asyncio
    async def test_check_text_done_pdf_service_error(self) -> None:
        self.telegram_message.text = self.DONE
        self.file_data_list.__len__.return_value = 2
        self.telegram_service.get_user_data.return_value = self.file_data_list
        self.pdf_service.merge_pdfs.side_effect = PdfServiceError()

        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, self.MERGE_PDF_DATA
        )
        self.pdf_service.merge_pdfs.assert_called_once_with(self.file_data_list)
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_text_done_with_one_file_only(self) -> None:
        self.telegram_message.text = self.DONE
        self.file_data_list.__len__.return_value = 1
        self.telegram_service.get_user_data.return_value = self.file_data_list

        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_MERGE_PDF
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, self.MERGE_PDF_DATA
        )
        self.pdf_service.merge_pdfs.assert_not_called()
        self.telegram_service.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_text_done_without_files(self) -> None:
        self.telegram_message.text = self.DONE
        self.file_data_list.__len__.return_value = 0
        self.telegram_service.get_user_data.return_value = self.file_data_list

        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == self.WAIT_MERGE_PDF
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, self.MERGE_PDF_DATA
        )
        self.pdf_service.merge_pdfs.assert_not_called()
        self.telegram_service.send_file.assert_not_called()
        self._assert_ask_first_pdf()

    @pytest.mark.asyncio
    async def test_check_text_cancel(self) -> None:
        self.telegram_message.text = self.CANCEL
        self.telegram_service.cancel_conversation.return_value = ConversationHandler.END

        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.cancel_conversation.assert_called_once_with(
            self.telegram_update, self.telegram_context
        )

    @pytest.mark.asyncio
    async def test_check_text_unknown_text(self) -> None:
        self.telegram_message.text = "clearly_unknown"
        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)
        assert actual == self.WAIT_MERGE_PDF

    @pytest.mark.parametrize("text", [REMOVE_LAST_FILE, DONE])
    @pytest.mark.asyncio
    async def test_check_text_telegram_service_error(self, text: str) -> None:
        self.telegram_message.text = text
        self.telegram_service.get_user_data.side_effect = TelegramServiceError()

        actual = await self.sut.check_text(self.telegram_update, self.telegram_context)

        assert actual == ConversationHandler.END
        self.telegram_service.get_user_data.assert_called_once_with(
            self.telegram_context, self.MERGE_PDF_DATA
        )
        self.telegram_update.effective_message.reply_text.assert_called_once()

    def _assert_ask_first_pdf(self) -> None:
        self.telegram_context.user_data.__setitem__.assert_called_with(
            self.MERGE_PDF_DATA, []
        )
        self.telegram_service.reply_with_cancel_markup.assert_called_once()
