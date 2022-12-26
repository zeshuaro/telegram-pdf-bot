import os
from gettext import gettext as _

from dotenv import load_dotenv
from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import ContextTypes

from pdf_bot.language import LanguageService

from .models import PaymentData

load_dotenv()
STRIPE_TOKEN = os.environ.get("STRIPE_TOKEN")


class PaymentService:
    _INVOICE_PAYLOAD = "invoice_payload"
    _CURRENCY = "USD"
    _PAYMENT_MESSAGE = _("{message} {emoji} (${value})")
    _KEYBOARD_SIZE = 2

    _PAYMENT_DATA_LIST = [
        PaymentData(_("Say Thanks"), "😁", 1),
        PaymentData(_("Coffee"), "☕", 3),
        PaymentData(_("Beer"), "🍺", 5),
        PaymentData(_("Meal"), "🍲", 10),
    ]

    def __init__(self, language_service: LanguageService) -> None:
        self.language_service = language_service

    async def send_support_options(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        query: CallbackQuery | None = None,
    ) -> None:
        _ = self.language_service.set_app_language(update, context)
        keyboard = [
            [
                InlineKeyboardButton(
                    _(self._PAYMENT_MESSAGE).format(
                        message=_(data.message), emoji=data.emoji, value=data.value
                    ),
                    callback_data=f"payment,{_(data.message)},{data.value}",
                )
                for data in self._PAYMENT_DATA_LIST[i : i + self._KEYBOARD_SIZE]
            ]
            for i in range(0, len(self._PAYMENT_DATA_LIST), self._KEYBOARD_SIZE)
        ]
        keyboard.append(
            [
                InlineKeyboardButton(
                    _("Help translate PDF Bot"), "https://crwd.in/telegram-pdf-bot"
                )
            ],
        )
        reply_markup = InlineKeyboardMarkup(keyboard)

        if query is None:
            user_id = update.effective_message.from_user.id  # type: ignore
        else:
            user_id = query.from_user.id

        await context.bot.send_message(
            user_id,
            _("Select how you want to support PDF Bot"),
            reply_markup=reply_markup,
        )

    async def send_invoice(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        query: CallbackQuery,
    ) -> None:
        _ = self.language_service.set_app_language(update, context)
        support_message, price = query.data.split(",")[1:]
        prices = [LabeledPrice(support_message, int(price) * 100)]

        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title=_("Support PDF Bot"),
            description=_("Say thanks to PDF Bot and help keep it running"),
            payload=self._INVOICE_PAYLOAD,
            provider_token=STRIPE_TOKEN,  # type: ignore
            currency=self._CURRENCY,
            prices=prices,
            max_tip_amount=1000,
            suggested_tip_amounts=[100, 300, 500, 1000],
        )

    async def precheckout_check(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        _ = self.language_service.set_app_language(update, context)
        query = update.pre_checkout_query

        if query.invoice_payload != self._INVOICE_PAYLOAD:
            await query.answer(
                ok=False, error_message=_("Something went wrong, try again")
            )
        else:
            await query.answer(ok=True)

    async def successful_payment(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        _ = self.language_service.set_app_language(update, context)
        await update.effective_message.reply_text(  # type: ignore
            _("Thank you for your support!"), reply_markup=ReplyKeyboardRemove()
        )
