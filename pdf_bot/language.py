import gettext

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from pdf_bot.constants import USER, LANGUAGE, LANGUAGES
from pdf_bot.store import client


def send_lang(update, context):
    lang = get_lang(update, context)
    langs = [InlineKeyboardButton(key, callback_data=key) for key, value in LANGUAGES.items() if value != lang]
    keyboard_size = 2
    keyboard = [langs[i:i + keyboard_size] for i in range(0, len(langs), keyboard_size)]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.effective_message.reply_text('Select your language', reply_markup=reply_markup)


def get_lang(update, context):
    if LANGUAGE in context.user_data:
        lang = context.user_data[LANGUAGE]
    else:
        user_key = client.key(USER, update.effective_message.from_user.id)
        user = client.get(key=user_key)

        if user is None or LANGUAGE not in user:
            lang = 'en'
        else:
            lang = user[LANGUAGE]

        context.user_data[LANGUAGE] = lang

    return lang


def store_lang(update, context, query):
    lang_code = LANGUAGES[query.data]
    with client.transaction():
        user_key = client.key(USER, query.from_user.id)
        user = client.get(key=user_key)
        user[LANGUAGE] = lang_code
        client.put(user)

    context.user_data[LANGUAGE] = lang_code
    _ = set_lang(update, context)
    query.message.edit_text(_('Your language has been set to {}').format(query.data))


def set_lang(update, context):
    lang = get_lang(update, context)
    t = gettext.translation('pdf_bot', localedir='locale', languages=[lang])

    return t.gettext
