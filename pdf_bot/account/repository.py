from google.cloud import datastore
from google.cloud.datastore import Client
from telegram import User

from pdf_bot.consts import LANGS_SHORT, LANGUAGE, USER
from pdf_bot.db import db


class AccountRepository:
    def __init__(self, db_client: Client | None = None):
        self.db = db_client or db

    def create_user(self, telegram_user: User) -> None:
        user_lang_code = telegram_user.language_code
        lang_code = "en_GB"

        if (
            user_lang_code is not None
            and user_lang_code != "en"
            and user_lang_code in LANGS_SHORT
        ):
            lang_code = LANGS_SHORT[user_lang_code]

        with self.db.transaction():
            key = self.db.key(USER, telegram_user.id)
            db_user = self.db.get(key=key)

            if db_user is None:
                db_user = datastore.Entity(key)
            if LANGUAGE not in db_user:
                db_user[LANGUAGE] = lang_code

            self.db.put(db_user)


account_repository = AccountRepository()
