from google.cloud import datastore

from pdf_bot.constants import USER, COUNT


def update_stats(update, gcp_key_file, add_count=True):
    client = datastore.Client.from_service_account_json(gcp_key_file)
    user_key = client.key(USER, update.message.from_user.id)
    user = client.get(key=user_key)

    if user is None:
        user = datastore.Entity(user_key)
        user[COUNT] = 1
    else:
        if add_count:
            user[COUNT] += 1

    client.put(user)
