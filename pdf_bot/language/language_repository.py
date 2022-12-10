from google.cloud.datastore import Client, Entity

from pdf_bot.consts import LANGUAGE, USER
from pdf_bot.db import db as default_db


class LanguageRepository:
    EN_GB_CODE = "en_GB"
    EN_CODE = "en"

    def __init__(self, database_client: Client | None = None):
        self.db = database_client or default_db

    def get_language(self, user_id: int) -> str:
        user_key = self.db.key(USER, user_id)
        user = self.db.get(key=user_key)

        if user is None or LANGUAGE not in user:
            lang = self.EN_GB_CODE
        else:
            lang = user[LANGUAGE]
            if lang == self.EN_CODE:
                lang = self.EN_GB_CODE

        return lang

    def upsert_language(self, user_id: int, language_code: str) -> None:
        with self.db.transaction():
            user_key = self.db.key(USER, user_id)
            user = self.db.get(key=user_key)
            if user is None:
                user = Entity(user_key)
            user[LANGUAGE] = language_code
            self.db.put(user)
