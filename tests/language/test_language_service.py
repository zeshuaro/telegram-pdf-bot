from unittest.mock import MagicMock, patch

import pytest

from pdf_bot.language import LanguageData, LanguageRepository, LanguageService
from tests.telegram_internal.telegram_test_mixin import TelegramTestMixin


class TestLanguageService(TelegramTestMixin):
    LANGUAGE_CODE = "language_code"
    EN_CODE = "en_US"
    LANGUAGE_DATA = LanguageData(label="label", long_code=EN_CODE)

    def setup_method(self) -> None:
        super().setup_method()
        self.language_repository = MagicMock(spec=LanguageRepository)
        self.language_repository.get_language.return_value = self.EN_CODE

        self.sut = LanguageService(self.language_repository)

        self.gettext_patcher = patch("pdf_bot.language.language_service.gettext")
        self.gettext_patcher.start()

    def teardown_method(self) -> None:
        self.gettext_patcher.stop()
        super().teardown_method()

    @pytest.mark.parametrize("value,expected", [("es", "es_ES"), ("clearly_invalid", None)])
    def test_get_language_code_from_short_code(self, value: str, expected: str | None) -> None:
        actual = self.sut.get_language_code_from_short_code(value)
        assert actual == expected

    @pytest.mark.asyncio
    async def test_send_language_options(self) -> None:
        self.telegram_update.callback_query = None

        await self.sut.send_language_options(self.telegram_update, self.telegram_context)

        self.telegram_callback_query.answer.assert_not_called()
        self.telegram_context.drop_callback_data.assert_not_called()
        self.telegram_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_language_options_with_callback_query(self) -> None:
        self.telegram_update.callback_query = self.telegram_callback_query

        await self.sut.send_language_options(self.telegram_update, self.telegram_context)

        self.telegram_callback_query.answer.assert_called_once()
        self.telegram_context.drop_callback_data.assert_not_called()
        self.telegram_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_language(self) -> None:
        self.telegram_user_data.get.return_value = None

        actual = self.sut.get_user_language(self.telegram_update, self.telegram_context)

        assert actual == self.EN_CODE
        self.telegram_user_data.__setitem__.assert_called_once_with(
            self.sut._LANGUAGE_CODE, self.EN_CODE
        )

    @pytest.mark.asyncio
    async def test_get_user_language_cached(self) -> None:
        self.telegram_user_data.get.return_value = self.EN_CODE

        actual = self.sut.get_user_language(self.telegram_update, self.telegram_context)

        assert actual == self.EN_CODE
        self.telegram_user_data.__setitem__.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_user_language_without_user_data(self) -> None:
        self.telegram_context.user_data = None

        actual = self.sut.get_user_language(self.telegram_update, self.telegram_context)

        assert actual == self.EN_CODE
        self.telegram_user_data.__setitem__.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_user_language_without_callback_query(self) -> None:
        self.telegram_user_data.get.return_value = None
        self.telegram_update.callback_query = None

        actual = self.sut.get_user_language(self.telegram_update, self.telegram_context)

        assert actual == self.EN_CODE
        self.telegram_user_data.__setitem__.assert_called_once_with(
            self.sut._LANGUAGE_CODE, self.EN_CODE
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("side_effect", [None, KeyError])
    async def test_update_user_language(self, side_effect: type[Exception] | None) -> None:
        self.telegram_callback_query.data = self.LANGUAGE_DATA
        self.telegram_context.drop_callback_data.side_effect = side_effect

        await self.sut.update_user_language(self.telegram_update, self.telegram_context)

        self.telegram_callback_query.answer.assert_called_once()
        self.telegram_context.drop_callback_data.assert_called_once_with(
            self.telegram_callback_query
        )
        self.language_repository.upsert_language.assert_called_once_with(
            self.TELEGRAM_QUERY_USER_ID, self.EN_CODE
        )
        self.telegram_user_data.__setitem__.assert_called_once_with(
            self.LANGUAGE_CODE, self.EN_CODE
        )

    @pytest.mark.asyncio
    async def test_update_user_language_without_user_data(self) -> None:
        self.telegram_callback_query.data = self.LANGUAGE_DATA
        self.telegram_context.user_data = None

        await self.sut.update_user_language(self.telegram_update, self.telegram_context)

        self.language_repository.upsert_language.assert_called_once_with(
            self.TELEGRAM_QUERY_USER_ID, self.EN_CODE
        )
        self.telegram_user_data.__setitem__.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_user_language_invalid_callback_query_data(self) -> None:
        self.telegram_callback_query.data = None

        with pytest.raises(TypeError):
            await self.sut.update_user_language(self.telegram_update, self.telegram_context)

            self.language_repository.upsert_language.assert_not_called()
            self.telegram_user_data.__setitem__.assert_not_called()
