from gettext import gettext as _

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import ContextTypes

from pdf_bot.language import LanguageService
from pdf_bot.telegram_internal import TelegramService

from .models import PaymentData


class PaymentService:
    _INVOICE_PAYLOAD = "invoice_payload"
    _CURRENCY = "USD"
    _PAYMENT_MESSAGE = _("{message} {emoji} (${value})")
    _KEYBOARD_SIZE = 2

    _PAYMENT_DATA_LIST = [
        PaymentData(label=_("Say Thanks"), emoji="😁", value=1),
        PaymentData(label=_("Coffee"), emoji="☕", value=3),
        PaymentData(label=_("Beer"), emoji="🍺", value=5),
        PaymentData(label=_("Meal"), emoji="🍲", value=10),
    ]

    def __init__(
        self,
        language_service: LanguageService,
        telegram_service: TelegramService,
        stripe_token: str,
    ) -> None:
        self.language_service = language_service
        self.telegram_service = telegram_service
        self.stripe_token = stripe_token

    async def send_support_options(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query

        # This method is used by both command and callback query handlers, so we need to
        # check if query is `None` here
        if query is not None:
            await query.answer()

        _ = self.language_service.set_app_language(update, context)
        reply_markup = self._get_support_options_markup(update, context)
        await update.effective_message.reply_text(  # type: ignore
            _("Select how you want to support PDF Bot"), reply_markup=reply_markup
        )

    async def send_invoice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await self.telegram_service.answer_query_and_drop_data(context, query)
        data: PaymentData = query.data  # type: ignore

        if not isinstance(data, PaymentData):
            raise TypeError(f"Invalid callback query data: {data}")

        _ = self.language_service.set_app_language(update, context)
        prices = [LabeledPrice(data.label, data.value * 100)]

        await update.effective_message.reply_invoice(  # type: ignore
            title=_("Support PDF Bot"),
            description=_("Say thanks to PDF Bot and help keep it running"),
            payload=self._INVOICE_PAYLOAD,
            provider_token=self.stripe_token,
            currency=self._CURRENCY,
            prices=prices,
            max_tip_amount=1000,
            suggested_tip_amounts=[100, 300, 500, 1000],
        )

    async def precheckout_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        _ = self.language_service.set_app_language(update, context)
        query = update.pre_checkout_query

        if query.invoice_payload != self._INVOICE_PAYLOAD:
            await query.answer(ok=False, error_message=_("Something went wrong, try again"))
        else:
            await query.answer(ok=True)

    async def successful_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        _ = self.language_service.set_app_language(update, context)
        await update.effective_message.reply_text(  # type: ignore
            _("Thank you for your support!"), reply_markup=ReplyKeyboardRemove()
        )

    def _get_support_options_markup(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> InlineKeyboardMarkup:
        _ = self.language_service.set_app_language(update, context)
        keyboard = [
            [
                InlineKeyboardButton(
                    _(self._PAYMENT_MESSAGE).format(
                        message=_(data.label), emoji=data.emoji, value=data.value
                    ),
                    callback_data=data,
                )
                for data in self._PAYMENT_DATA_LIST[i : i + self._KEYBOARD_SIZE]
            ]
            for i in range(0, len(self._PAYMENT_DATA_LIST), self._KEYBOARD_SIZE)
        ]
        keyboard.append(
            [InlineKeyboardButton(_("Help translate PDF Bot"), "https://crwd.in/telegram-pdf-bot")]
        )

        return InlineKeyboardMarkup(keyboard)
