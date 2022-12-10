from unittest.mock import MagicMock, patch

from pdf_bot.language import LanguageRepository, LanguageService
from tests.telegram_internal.telegram_test_mixin import TelegramTestMixin


class TestLanguageRService(TelegramTestMixin):
    @classmethod
    def setup_class(cls) -> None:
        super().setup_class()
        cls.valid_lang = "🇺🇸 English (US)"
        cls.valid_lang_code = "en_US"
        cls.gettext_patcher = patch("pdf_bot.language.language_service.gettext")
        cls.gettext_patcher.start()

    @classmethod
    def teardown_class(cls) -> None:
        cls.gettext_patcher.stop()
        super().teardown_class()

    def setup_method(self) -> None:
        super().setup_method()
        self.language_repository = MagicMock(spec=LanguageRepository)
        self.language_repository.get_language.return_value = self.valid_lang_code

        self.sut = LanguageService(self.language_repository)

    def test_send_language_options(self) -> None:
        self.sut.send_language_options(self.telegram_update, self.telegram_context)
        self.telegram_update.effective_message.reply_text.assert_called_once()

    def test_get_user_language(self) -> None:
        actual = self.sut.get_user_language(self.telegram_update, self.telegram_context)

        assert actual == self.valid_lang_code
        self.telegram_user_data.__setitem__.assert_called_once_with(
            self.sut.LANGUAGE, self.valid_lang_code
        )

    def test_get_user_language_cached(self) -> None:
        cached_lang = "cached_lang"
        user_data = {self.sut.LANGUAGE: cached_lang}
        self.telegram_user_data.__getitem__.side_effect = user_data.__getitem__
        self.telegram_user_data.__contains__.side_effect = user_data.__contains__

        actual = self.sut.get_user_language(self.telegram_update, self.telegram_context)

        assert actual == cached_lang
        self.telegram_user_data.__setitem__.assert_not_called()

    def test_get_user_language_from_query(self) -> None:
        actual = self.sut.get_user_language(
            self.telegram_update, self.telegram_context, self.telegram_callback_query
        )

        assert actual == self.valid_lang_code
        self.telegram_user_data.__setitem__.assert_called_once_with(
            self.sut.LANGUAGE, self.valid_lang_code
        )

    def test_update_user_language(self) -> None:
        self.telegram_callback_query.data = self.valid_lang
        user_data = {self.sut.LANGUAGE: self.valid_lang_code}
        self.telegram_user_data.__getitem__.side_effect = user_data.__getitem__
        self.telegram_user_data.__contains__.side_effect = user_data.__contains__

        self.sut.update_user_language(
            self.telegram_update, self.telegram_context, self.telegram_callback_query
        )

        self.language_repository.upsert_language.assert_called_once_with(
            self.telegram_query_user_id, self.valid_lang_code
        )
        self.telegram_user_data.__setitem__.assert_called_once_with(
            self.sut.LANGUAGE, self.valid_lang_code
        )

    def test_update_user_language_invalid_language(self) -> None:
        self.telegram_callback_query.data = "clearly_invalid"

        self.sut.update_user_language(
            self.telegram_update, self.telegram_context, self.telegram_callback_query
        )

        self.language_repository.upsert_language.assert_not_called()
        self.telegram_user_data.__setitem__.assert_not_called()
