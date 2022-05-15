from telegram import User

from pdf_bot.account.account_repository import AccountRepository, account_repository
from pdf_bot.consts import LANGS_SHORT


class AccountService:
    _LANGUAGE_CODE = "en_GB"

    def __init__(self, repository: AccountRepository | None = None) -> None:
        self.repository = repository or account_repository

    def create_user(self, telegram_user: User) -> None:
        user_lang_code = telegram_user.language_code
        lang_code = self._LANGUAGE_CODE

        if (
            user_lang_code is not None
            and user_lang_code != "en"
            and user_lang_code in LANGS_SHORT
        ):
            lang_code = LANGS_SHORT[user_lang_code]

        self.repository.upsert_user(telegram_user.id, lang_code)


account_service = AccountService()
