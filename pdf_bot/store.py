import os

from dotenv import load_dotenv
from google.cloud import datastore

from pdf_bot.constants import USER, LANGUAGE


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


def create_user(user_id):
    user_key = client.key(USER, user_id)
    with client.transaction():
        user = client.get(key=user_key)
        if user is None:
            user = datastore.Entity(user_key)
            user[LANGUAGE] = "en"

        client.put(user)
