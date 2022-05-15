from google.cloud import datastore
from google.cloud.datastore import Client

from pdf_bot.consts import LANGUAGE, USER
from pdf_bot.db import db


class AccountRepository:
    def __init__(self, db_client: Client | None = None):
        self.db = db_client or db

    def upsert_user(self, user_id: int, language_code: str) -> None:
        with self.db.transaction():
            key = self.db.key(USER, user_id)
            db_user = self.db.get(key=key)

            if db_user is None:
                db_user = datastore.Entity(key)
            if LANGUAGE not in db_user:
                db_user[LANGUAGE] = language_code

            self.db.put(db_user)


account_repository = AccountRepository()
