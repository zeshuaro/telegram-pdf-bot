#!/usr/bin/env python3

import dotenv
import os

from textblob import TextBlob
from textblob.exceptions import TranslatorError
from slackclient import SlackClient
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async


dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
dotenv.load_dotenv(dotenv_path)

slack_token = os.environ.get("SLACK_TOKEN")
bot_name = os.environ.get("BOT_NAME")


# Creates a feedback conversation handler
def feedback_cov_handler():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('feedback', feedback)],
        states={0: [MessageHandler(Filters.text, receive_feedback)]},
        fallbacks=[CommandHandler("cancel", cancel_feedback)]
    )

    return conv_handler


# Sends a feedback message
@run_async
def feedback(bot, update):
    text = "Please send me your feedback or type /cancel to cancel this operation. " \
           "My developer can understand English and Chinese."
    update.message.reply_text(text)

    return 0


# Saves a feedback
@run_async
def receive_feedback(bot, update):
    global bot_name
    tele_username = update.message.chat.username
    feedback_msg = update.message.text
    feedback_lang = None
    valid_langs = ("en", "zh-hk", "zh-tw", "zh-cn")
    b = TextBlob(feedback_msg)

    try:
        feedback_lang = b.detect_language()
    except TranslatorError:
        pass

    if not feedback_lang or feedback_lang.lower() not in valid_langs:
        update.message.reply_text("The feedback you sent is not in English or Chinese. Please try again.")
        return 0

    sc = SlackClient(slack_token)
    sc.api_call(
        "chat.postMessage",
        channel="#bots_feedback",
        text=f"{bot_name} Feedback",
        attachments=[{
            "text": f"Feedback received from @{tele_username}\n\n{feedback_msg}"
        }]
    )

    update.message.reply_text("Thank you for your feedback, I've already forwarded it to my developer.")

    return ConversationHandler.END


# Cancels feedback operation
@run_async
def cancel_feedback(bot, update):
    update.message.reply_text("Feedback operation cancelled.")
    return ConversationHandler.END
