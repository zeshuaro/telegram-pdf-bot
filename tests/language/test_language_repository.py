from typing import Any
from unittest.mock import MagicMock, patch

from google.cloud.datastore import Client, Entity

from pdf_bot.consts import LANGUAGE
from pdf_bot.language import LanguageRepository


class TestLanguageRepository:
    @classmethod
    def setup_class(cls) -> None:
        cls.user_id = 0
        cls.lang_code = "lang_code"
        cls.user_entity_dict = {LANGUAGE: cls.lang_code}

    def setup_method(self) -> None:
        self.user_entity = MagicMock(spec=Entity)
        self.db_client = MagicMock(spec=Client)

        self.sut = LanguageRepository(self.db_client)

    def test_get_language(self) -> None:
        self._mock_user_entity_dict()
        self.db_client.get.return_value = self.user_entity

        actual = self.sut.get_language(self.user_id)

        assert actual == self.lang_code

    def test_get_language_without_user(self) -> None:
        self.db_client.get.return_value = None
        actual = self.sut.get_language(self.user_id)
        assert actual == self.sut.EN_GB_CODE

    def test_get_language_and_language_not_set(self) -> None:
        self.db_client.get.return_value = self.user_entity
        actual = self.sut.get_language(self.user_id)
        assert actual == self.sut.EN_GB_CODE

    def test_get_language_legacy_en_code(self) -> None:
        user_entity_dict = {LANGUAGE: "en"}
        self._mock_user_entity_dict(user_entity_dict)
        self.db_client.get.return_value = self.user_entity

        actual = self.sut.get_language(self.user_id)

        assert actual == self.sut.EN_GB_CODE

    def test_upsert_language(self) -> None:
        self.db_client.get.return_value = self.user_entity

        self.sut.upsert_language(self.user_id, self.lang_code)

        self.user_entity.__setitem__.assert_called_with(LANGUAGE, self.lang_code)
        self.db_client.put.assert_called_once_with(self.user_entity)

    def test_upsert_language_without_user(self) -> None:
        self.db_client.get.return_value = None

        with patch("pdf_bot.language.language_repository.Entity") as entity_cls:
            entity_cls.return_value = self.user_entity
            self.sut.upsert_language(self.user_id, self.lang_code)

        entity_cls.assert_called_once()
        self.user_entity.__setitem__.assert_called_with(LANGUAGE, self.lang_code)
        self.db_client.put.assert_called_once_with(self.user_entity)

    def _mock_user_entity_dict(
        self, user_entity_dict: dict[str, Any] | None = None
    ) -> None:
        if user_entity_dict is None:
            user_entity_dict = self.user_entity_dict
        self.user_entity.__getitem__.side_effect = user_entity_dict.__getitem__
        self.user_entity.__contains__.side_effect = user_entity_dict.__contains__
