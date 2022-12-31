from telegram import User

from pdf_bot.account.account_repository import AccountRepository
from pdf_bot.language import LanguageService


class AccountService:
    _LANGUAGE_CODE = "en_GB"

    def __init__(
        self, account_repository: AccountRepository, language_service: LanguageService
    ) -> None:
        self.account_repository = account_repository
        self.language_service = language_service

    def create_user(self, telegram_user: User) -> None:
        user_lang_code = telegram_user.language_code
        lang_code = self._LANGUAGE_CODE

        if user_lang_code is not None and user_lang_code != "en":
            code = self.language_service.get_language_code_from_short_code(user_lang_code)
            if code is not None:
                lang_code = code

        self.account_repository.upsert_user(telegram_user.id, lang_code)
