import os
import sys

from dotenv import load_dotenv
from google.cloud import datastore

load_dotenv()
GCP_KEY_FILE = os.environ.get("GCP_KEY_FILE")
GCP_CRED = os.environ.get("GCP_CRED")

if GCP_CRED is not None and GCP_KEY_FILE is not None:
    with open(GCP_KEY_FILE, "w") as f:
        f.write(GCP_CRED)

if "pytest" in sys.modules:
    db = None
elif GCP_KEY_FILE is not None:
    db = datastore.Client.from_service_account_json(GCP_KEY_FILE)
else:
    db = datastore.Client()
