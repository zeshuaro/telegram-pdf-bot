import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import os
import tempfile

from collections import defaultdict
from datetime import date
from dotenv import load_dotenv
from google.cloud import datastore

from pdf_bot.store import client
from pdf_bot.constants import USER, LANGUAGE, LANGUAGES

load_dotenv()
DEV_TELE_ID = int(os.environ.get("DEV_TELE_ID"))


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
    langs = defaultdict(int)

    for user in query.fetch():
        if user.key.id != DEV_TELE_ID:
            num_users += 1
            for key in user.keys():
                if key != LANGUAGE:
                    num_tasks += user[key]
                    if key != "count":
                        counts[key] += user[key]
                elif key == LANGUAGE:
                    langs[user[key]] += 1

    launch_date = date(2017, 7, 1)
    stats_date = date(2019, 7, 1)
    curr_date = date.today()

    launch_diff = (curr_date - launch_date).days
    stats_diff = (curr_date - stats_date).days
    est_num_tasks = int(num_tasks / stats_diff * launch_diff * 0.8)

    update.effective_message.reply_text(
        f"Total users: {num_users:,}\nTotal tasks: {num_tasks:,}\n"
        f"Estimated total tasks: {est_num_tasks:,}"
    )

    text = "Language stats:\n"
    for key, value in LANGUAGES.items():
        if value in langs:
            text += f"{key}: {langs[value]:,}\n"

    update.effective_message.reply_text(text)
    send_plot(update, counts)


def send_plot(update, counts):
    tasks = sorted(counts.keys())
    nums = [counts[x] for x in tasks]
    y_pos = list(range(len(tasks)))

    plt.rcdefaults()
    _, ax = plt.subplots()

    ax.barh(y_pos, nums, align="center")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(tasks)
    ax.set_xlabel("Counts")
    ax.set_ylabel("Tasks")
    ax.invert_yaxis()
    ax.set_title("PDF Bot Statistics")
    ax.get_xaxis().set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda x, _: f"{int(x):,}")
    )
    plt.tight_layout()

    with tempfile.NamedTemporaryFile(suffix=".png") as tf:
        plt.savefig(tf.name)
        update.effective_message.reply_photo(open(tf.name, "rb"))
