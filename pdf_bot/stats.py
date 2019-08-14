import os

from datetime import date
from dotenv import load_dotenv
from google.cloud import datastore

from pdf_bot.constants import USER, COUNT


load_dotenv()
GCP_KEY_FILE = os.environ.get('GCP_KEY_FILE')
GCP_CRED = os.environ.get('GCP_CRED')

if GCP_CRED is not None:
    with open(GCP_KEY_FILE, 'w') as f:
        f.write(GCP_CRED)


def update_stats(update, add_count=True):
    client = datastore.Client.from_service_account_json(GCP_KEY_FILE)
    user_key = client.key(USER, update.message.from_user.id)
    user = client.get(key=user_key)

    if user is None:
        user = datastore.Entity(user_key)
        user[COUNT] = 1
    else:
        if add_count:
            user[COUNT] += 1

    client.put(user)


def get_stats(update, _):
    client = datastore.Client.from_service_account_json(GCP_KEY_FILE)
    query = client.query(kind=USER)
    num_users = num_tasks = 0

    for user in query.fetch():
        num_users += 1
        num_tasks += user[COUNT]

    launch_date = date(2017, 7, 1)
    stats_date = date(2019, 7, 1)
    curr_date = date.today()

    launch_diff = (curr_date - launch_date).days
    stats_diff = (curr_date - stats_date).days
    est_num_tasks = int(num_tasks / stats_diff * launch_diff * 0.8)

    update.message.reply_text(
        f'Total users: {num_users}\nTotal tasks: {num_tasks}\nEstimated total tasks: {est_num_tasks}')
