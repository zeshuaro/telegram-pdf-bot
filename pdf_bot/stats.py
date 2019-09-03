import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import tempfile

from collections import defaultdict
from datetime import date
from google.cloud import datastore

from pdf_bot.store import client
from pdf_bot.constants import USER, LANGUAGE


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
    counts = defaultdict(int)

    for user in query.fetch():
        num_users += 1
        for key in user.keys():
            if key != LANGUAGE:
                num_tasks += user[key]
                if key != 'count':
                    counts[key] += user[key]

    launch_date = date(2017, 7, 1)
    stats_date = date(2019, 7, 1)
    curr_date = date.today()

    launch_diff = (curr_date - launch_date).days
    stats_diff = (curr_date - stats_date).days
    est_num_tasks = int(num_tasks / stats_diff * launch_diff * 0.8)

    update.effective_message.reply_text(
        f'Total users: {num_users}\nTotal tasks: {num_tasks}\nEstimated total tasks: {est_num_tasks}')
    send_plot(update, counts)


def send_plot(update, counts):
    tasks = sorted(counts.keys())
    nums = [counts[x] for x in tasks]
    x_pos = list(range(len(tasks)))

    plt.rcdefaults()
    fig, ax = plt.subplots()

    ax.bar(x_pos, nums, align='center')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(tasks)
    ax.set_xlabel('Tasks')
    ax.set_ylabel('Counts')

    with tempfile.NamedTemporaryFile(suffix='.png') as tf:
        plt.savefig(tf.name)
        update.effective_message.reply_photo(open(tf.name, 'rb'))
