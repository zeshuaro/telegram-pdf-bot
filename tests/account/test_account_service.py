from unittest.mock import MagicMock

from telegram import User

from pdf_bot.account import AccountRepository, AccountService


class TestAccountService:
    @classmethod
    def setup_class(cls) -> None:
        cls.lang_code = "en_GB"
        cls.user_id = 0

    def setup_method(self) -> None:
        self.user = MagicMock(spec=User)
        self.user.id = self.user_id

        self.repo = MagicMock(spec=AccountRepository)
        self.service = AccountService(self.repo)

    def test_create_user(self) -> None:
        self.service.create_user(self.user)
        self.repo.upsert_user.assert_called_with(self.user_id, self.lang_code)

    def test_create_user_with_language_code(self) -> None:
        self.user.language_code = "it"
        self.service.create_user(self.user)
        self.repo.upsert_user.assert_called_with(self.user_id, "it_IT")

    def test_create_user_with_invalid_language_code(self) -> None:
        self.user.language_code.return_value = "clearly_invalid_code"
        self.service.create_user(self.user)
        self.repo.upsert_user.assert_called_with(self.user_id, self.lang_code)
