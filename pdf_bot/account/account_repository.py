from typing import cast

from google.cloud.datastore import Client, Entity

from pdf_bot.consts import LANGUAGE, USER
from pdf_bot.db import db as default_db


class AccountRepository:
    def __init__(self, database_client: Client | None = None):
        self.db = cast(Client, database_client or default_db)

    def get_user(self, user_id: int) -> Entity | None:
        key = self.db.key(USER, user_id)
        return self.db.get(key)  # type: ignore

    def upsert_user(self, user_id: int, language_code: str) -> None:
        with self.db.transaction():
            key = self.db.key(USER, user_id)
            db_user = self.db.get(key)

            if db_user is None:
                db_user = Entity(key)
            if LANGUAGE not in db_user:
                db_user[LANGUAGE] = language_code

            self.db.put(db_user)
