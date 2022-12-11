from unittest.mock import MagicMock

from telegram import User

from pdf_bot.account import AccountRepository, AccountService


class TestAccountService:
    LANGUAGE_CODE = "en_GB"
    USER_ID = 0

    def setup_method(self) -> None:
        self.user = MagicMock(spec=User)
        self.user.id = self.USER_ID

        self.repo = MagicMock(spec=AccountRepository)
        self.service = AccountService(self.repo)

    def test_create_user(self) -> None:
        self.service.create_user(self.user)
        self.repo.upsert_user.assert_called_with(self.USER_ID, self.LANGUAGE_CODE)

    def test_create_user_with_language_code(self) -> None:
        self.user.language_code = "it"
        self.service.create_user(self.user)
        self.repo.upsert_user.assert_called_with(self.USER_ID, "it_IT")

    def test_create_user_with_invalid_language_code(self) -> None:
        self.user.language_code.return_value = "clearly_invalid_code"
        self.service.create_user(self.user)
        self.repo.upsert_user.assert_called_with(self.USER_ID, self.LANGUAGE_CODE)
