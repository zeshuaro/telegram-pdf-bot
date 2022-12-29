from unittest.mock import MagicMock

from telegram import User

from pdf_bot.account import AccountRepository, AccountService
from tests.language import LanguageServiceTestMixin


class TestAccountService(LanguageServiceTestMixin):
    LANGUAGE_CODE = "en_GB"
    USER_ID = 0

    def setup_method(self) -> None:
        self.user = MagicMock(spec=User)
        self.user.id = self.USER_ID

        self.account_repository = MagicMock(spec=AccountRepository)
        self.language_service = self.mock_language_service()
        self.language_service.get_language_code_from_short_code.return_value = (
            self.LANGUAGE_CODE
        )

        self.service = AccountService(self.account_repository, self.language_service)

    def test_create_user(self) -> None:
        self.user.language_code = None
        self.service.create_user(self.user)
        self.account_repository.upsert_user.assert_called_with(
            self.USER_ID, self.LANGUAGE_CODE
        )

    def test_create_user_with_language_code(self) -> None:
        user_code = "user_code"
        self.user.language_code = user_code
        self.language_service.get_language_code_from_short_code.return_value = user_code

        self.service.create_user(self.user)

        self.account_repository.upsert_user.assert_called_with(self.USER_ID, user_code)

    def test_create_user_with_invalid_language_code(self) -> None:
        self.user.language_code = "clearly_invalid"
        self.language_service.get_language_code_from_short_code.return_value = None

        self.service.create_user(self.user)

        self.account_repository.upsert_user.assert_called_with(
            self.USER_ID, self.LANGUAGE_CODE
        )
