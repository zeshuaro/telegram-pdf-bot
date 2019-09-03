from datetime import date
from google.cloud import datastore

from pdf_bot.store import client
from pdf_bot.constants import USER


def update_stats(update, task):
    user_key = client.key(USER, update.effective_message.from_user.id)
    with client.transaction():
        user = client.get(key=user_key)
        if user is None:
            user = datastore.Entity(user_key)
            user[task] = 1
        else:
            if task in user:
                user[task] += 1
            else:
                user[task] = 1

        client.put(user)


def get_stats(update, context):
    query = client.query(kind=USER)
    num_users = num_tasks = 0

    for user in query.fetch():
        num_users += 1
        num_tasks += sum([x for x in user.values() if isinstance(x, int)])

    launch_date = date(2017, 7, 1)
    stats_date = date(2019, 7, 1)
    curr_date = date.today()

    launch_diff = (curr_date - launch_date).days
    stats_diff = (curr_date - stats_date).days
    est_num_tasks = int(num_tasks / stats_diff * launch_diff * 0.8)

    update.effective_message.reply_text(
        f'Total users: {num_users}\nTotal tasks: {num_tasks}\nEstimated total tasks: {est_num_tasks}')