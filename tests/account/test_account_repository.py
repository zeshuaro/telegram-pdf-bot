from unittest.mock import MagicMock, patch

from google.cloud.datastore import Client, Entity, Key

from pdf_bot.account import AccountRepository
from pdf_bot.consts import LANGUAGE


class TestAccountRepository:
    USER_ID = 0
    LANGUAGE_CODE = "lang_code"

    def setup_method(self) -> None:
        self.user_entity = MagicMock(spec=Entity)

        self.datastore_client = MagicMock(spec=Client)
        self.sut = AccountRepository(self.datastore_client)

    def test_get_user(self) -> None:
        self.datastore_client.get.return_value = self.user_entity
        actual = self.sut.get_user(self.USER_ID)
        assert actual == self.user_entity

    def test_get_user_null(self) -> None:
        self.datastore_client.get.return_value = None
        actual = self.sut.get_user(self.USER_ID)
        assert actual is None

    def test_upsert_user(self) -> None:
        user_dict: dict = {}
        self.user_entity.__contains__.side_effect = user_dict.__contains__
        self.datastore_client.get.return_value = self.user_entity

        self.sut.upsert_user(self.USER_ID, self.LANGUAGE_CODE)

        self.user_entity.__setitem__.assert_called_once_with(LANGUAGE, self.LANGUAGE_CODE)
        self.datastore_client.put.assert_called_with(self.user_entity)

    def test_upsert_user_language_exists(self) -> None:
        user_dict: dict = {LANGUAGE: self.LANGUAGE_CODE}
        self.user_entity.__contains__.side_effect = user_dict.__contains__
        self.datastore_client.get.return_value = self.user_entity

        self.sut.upsert_user(self.USER_ID, self.LANGUAGE_CODE)

        self.user_entity.__setitem__.assert_not_called()
        self.datastore_client.put.assert_called_with(self.user_entity)

    def test_upsert_user_new_user(self) -> None:
        key = MagicMock(spec=Key)
        self.datastore_client.key.return_value = key
        self.datastore_client.get.return_value = None

        with patch("pdf_bot.account.account_repository.Entity") as entity_cls:
            self.sut.upsert_user(self.USER_ID, self.LANGUAGE_CODE)

            entity_cls.assert_called_once_with(key)
            self.datastore_client.put.assert_called_once()
