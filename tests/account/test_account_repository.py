from unittest.mock import MagicMock

from google.cloud.datastore import Client, Entity, Key

from pdf_bot.account import AccountRepository


class TestAccountRepository:
    @classmethod
    def setup_class(cls) -> None:
        cls.user_id = 0
        cls.lang_code = "lang_code"

    def setup_method(self) -> None:
        key = Key("User", self.user_id, project="test")
        self.user_entity = Entity(key)

        self.db_client = MagicMock(spec=Client)
        self.repo = AccountRepository(self.db_client)

    def test_get_user(self) -> None:
        self.db_client.get.return_value = self.user_entity
        actual = self.repo.get_user(self.user_id)
        assert actual == self.user_entity

    def test_get_user_null(self) -> None:
        self.db_client.get.return_value = None
        actual = self.repo.get_user(self.user_id)
        assert actual is None

    def test_upsert_user(self) -> None:
        self.db_client.get.return_value = self.user_entity

        self.repo.upsert_user(self.user_id, self.lang_code)

        assert self.user_entity["language"] == self.lang_code
        self.db_client.put.assert_called_with(self.user_entity)

    def test_upsert_user_new_user(self) -> None:
        self.db_client.get.return_value = None
        self.repo.upsert_user(self.user_id, self.lang_code)
        self.db_client.put.assert_called_once()
