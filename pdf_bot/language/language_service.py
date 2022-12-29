import gettext
from typing import Callable

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from .language_repository import LanguageRepository
from .models import LanguageData


class LanguageService:
    _LANGUAGE_CODE = "language_code"
    _KEYBOARD_SIZE = 2

    _LANGUAGE_DATA_LIST = sorted(
        [
            LanguageData(label="🇬🇧 English (UK)", long_code="en_GB"),
            LanguageData(label="🇺🇸 English (US)", long_code="en_US"),
            LanguageData(label="🇭🇰 廣東話", long_code="zh_HK"),
            LanguageData(label="🇹🇼 繁體中文", long_code="zh_TW"),
            LanguageData(label="🇨🇳 简体中文", long_code="zh_CN"),
            LanguageData(label="🇮🇹 Italiano", long_code="it_IT"),
            LanguageData(label="🇦🇪 اَلْعَرَبِيَّةُ", long_code="ar_SA"),
            LanguageData(label="🇳🇱 Nederlands", long_code="nl_NL"),
            LanguageData(label="🇧🇷 Português do Brasil", long_code="pt_BR"),
            LanguageData(label="🇪🇸 español", long_code="es_ES"),
            LanguageData(label="🇹🇷 Türkçe", long_code="tr_TR"),
            LanguageData(label="🇮🇱 עברית", long_code="he_IL"),
            LanguageData(label="🇷🇺 русский язык", long_code="ru_RU"),
            LanguageData(label="🇫🇷 français", long_code="fr_FR"),
            LanguageData(label="🇱🇰 සිංහල", long_code="si_LK"),
            LanguageData(label="🇿🇦 Afrikaans", long_code="af_ZA"),
            LanguageData(label="català", long_code="ca_ES"),
            LanguageData(label="🇨🇿 čeština", long_code="cs_CZ"),
            LanguageData(label="🇩🇰 dansk", long_code="da_DK"),
            LanguageData(label="🇫🇮 suomen kieli", long_code="fi_FI"),
            LanguageData(label="🇩🇪 Deutsch", long_code="de_DE"),
            LanguageData(label="🇬🇷 ελληνικά", long_code="el_GR"),
            LanguageData(label="🇭🇺 magyar nyelv", long_code="hu_HU"),
            LanguageData(label="🇯🇵 日本語", long_code="ja_JP"),
            LanguageData(label="🇰🇷 한국어", long_code="ko_KR"),
            LanguageData(label="🇳🇴 norsk", long_code="no_NO"),
            LanguageData(label="🇵🇱 polski", long_code="pl_PL"),
            LanguageData(label="🇵🇹 português", long_code="pt_PT"),
            LanguageData(label="🇷🇴 Daco-Romanian", long_code="ro_RO"),
            LanguageData(label="🇸🇪 svenska", long_code="sv_SE"),
            LanguageData(label="🇺🇦 українська мова", long_code="uk_UA"),
            LanguageData(label="🇻🇳 Tiếng Việt", long_code="vi_VN"),
            LanguageData(label="🇮🇳 हिन्दी", long_code="hi_IN"),
            LanguageData(label="🇮🇩 bahasa Indonesia", long_code="id_ID"),
            LanguageData(label="🇺🇿 O'zbekcha", long_code="uz_UZ"),
            LanguageData(label="🇲🇾 Bahasa Melayu", long_code="ms_MY"),
            LanguageData(label="🇮🇳 தமிழ்", long_code="ta_IN"),
            LanguageData(label="🇪🇹 አማርኛ", long_code="am_ET"),
            LanguageData(label="🇰🇬 Кыргызча", long_code="ky_KG"),
        ],
        key=lambda x: x.long_code,
    )

    def __init__(self, language_repository: LanguageRepository) -> None:
        self.language_repository = language_repository

    def get_language_code_from_short_code(self, short_code: str) -> str | None:
        for data in self._LANGUAGE_DATA_LIST:
            if data.short_code == short_code:
                return data.long_code
        return None

    async def send_language_options(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        if query is not None:
            await query.answer()

        _ = self.set_app_language(update, context)
        reply_markup = self._get_languages_markup(update, context)
        await update.effective_message.reply_text(  # type: ignore
            _("Select your language"), reply_markup=reply_markup
        )

    def get_user_language(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str:
        user_data = context.user_data
        if user_data is not None:
            lang: str | None = user_data.get(self._LANGUAGE_CODE)
            if lang is not None:
                return lang

        user_id = self._get_user_id(update)
        lang = self.language_repository.get_language(user_id)

        if user_data is not None:
            user_data[self._LANGUAGE_CODE] = lang
        return lang

    async def update_user_language(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        await query.answer()
        data: LanguageData = query.data  # type: ignore

        if not isinstance(data, LanguageData):
            raise TypeError(f"Invalid callback query data: {data}")

        self.language_repository.upsert_language(query.from_user.id, data.long_code)
        if context.user_data is not None:
            context.user_data[self._LANGUAGE_CODE] = data.long_code

        _ = self.set_app_language(update, context)
        await query.edit_message_text(
            _("Your language has been set to {language}").format(language=data.label)
        )

    def set_app_language(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> Callable[[str], str]:
        lang = self.get_user_language(update, context)
        t = gettext.translation("pdf_bot", localedir="locale", languages=[lang])

        return t.gettext

    def _get_languages_markup(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> InlineKeyboardMarkup:
        user_lang = self.get_user_language(update, context)
        btns = [
            InlineKeyboardButton(data.label, callback_data=data)
            for data in self._LANGUAGE_DATA_LIST
            if data.long_code != user_lang
        ]

        keyboard = [
            btns[i : i + self._KEYBOARD_SIZE]
            for i in range(0, len(self._LANGUAGE_DATA_LIST), self._KEYBOARD_SIZE)
        ]

        return InlineKeyboardMarkup(keyboard)

    def _get_user_id(self, update: Update) -> int:
        query: CallbackQuery | None = update.callback_query
        if query is None:
            sender = update.effective_message.from_user or update.effective_chat  # type: ignore
            return sender.id  # type: ignore
        return query.from_user.id
