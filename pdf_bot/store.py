import os

from dotenv import load_dotenv
from google.cloud import datastore
from telegram import User

from pdf_bot.constants import LANGS_SHORT, LANGUAGE, USER

load_dotenv()
GCP_KEY_FILE = os.environ.get("GCP_KEY_FILE")
GCP_CRED = os.environ.get("GCP_CRED")

if GCP_CRED is not None:
    with open(GCP_KEY_FILE, "w") as f:
        f.write(GCP_CRED)

if GCP_KEY_FILE is not None:
    client = datastore.Client.from_service_account_json(GCP_KEY_FILE)
else:
    client = datastore.Client()


def create_user(tele_user: User) -> None:
    key = client.key(USER, tele_user.id)
    user_lang_code = tele_user.language_code
    lang_code = "en_GB"

    if (
        user_lang_code is not None
        and user_lang_code != "en"
        and user_lang_code in LANGS_SHORT
    ):
        lang_code = LANGS_SHORT[user_lang_code]

    with client.transaction():
        db_user = client.get(key=key)
        if db_user is None:
            db_user = datastore.Entity(key)
        if LANGUAGE not in db_user:
            db_user[LANGUAGE] = lang_code

        client.put(db_user)
