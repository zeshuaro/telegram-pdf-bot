import pytest
from telegram import InlineKeyboardMarkup

from pdf_bot.payment import PaymentData, PaymentService
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramServiceTestMixin, TelegramTestMixin


class TestPaymentService(
    LanguageServiceTestMixin, TelegramServiceTestMixin, TelegramTestMixin
):
    STRIPE_TOKEN = "stripe_token"
    INVOICE_PAYLOAD = "invoice_payload"
    PAYMENT_DATA = PaymentData(label="label", emoji="emoji", value=1)

    PAYMENT_AMOUNTS = [1, 3, 5, 10]

    def setup_method(self) -> None:
        super().setup_method()
        self.language_service = self.mock_language_service()
        self.telegram_service = self.mock_telegram_service()

        self.sut = PaymentService(
            self.language_service, self.telegram_service, self.STRIPE_TOKEN
        )

    @pytest.mark.asyncio
    async def test_send_support_options(self) -> None:
        self.telegram_update.callback_query = None

        await self.sut.send_support_options(self.telegram_update, self.telegram_context)

        self.telegram_callback_query.answer.assert_not_called()
        _args, kwargs = self.telegram_update.effective_message.reply_text.call_args

        reply_markup: InlineKeyboardMarkup | None = kwargs.get("reply_markup")
        assert reply_markup is not None
        self._assert_keyboard_payment_callback_data(reply_markup)

    @pytest.mark.asyncio
    async def test_send_support_options_with_callback_query(self) -> None:
        self.telegram_update.callback_query = self.telegram_callback_query

        await self.sut.send_support_options(self.telegram_update, self.telegram_context)

        self.telegram_service.answer_query_and_drop_data.assert_called_once_with(
            self.telegram_context, self.telegram_callback_query
        )
        _args, kwargs = self.telegram_update.effective_message.reply_text.call_args

        reply_markup: InlineKeyboardMarkup | None = kwargs.get("reply_markup")
        assert reply_markup is not None
        self._assert_keyboard_payment_callback_data(reply_markup)

    @pytest.mark.asyncio
    async def test_send_invoice(self) -> None:
        self.telegram_callback_query.data = self.PAYMENT_DATA
        await self.sut.send_invoice(self.telegram_update, self.telegram_context)

        self.telegram_service.answer_query_and_drop_data.assert_called_once_with(
            self.telegram_context, self.telegram_callback_query
        )
        self.telegram_update.effective_message.reply_invoice.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_invoice_invalid_callback_query_data(self) -> None:
        self.telegram_callback_query.data = None
        with pytest.raises(TypeError):
            await self.sut.send_invoice(self.telegram_update, self.telegram_context)
            self.telegram_update.effective_message.reply_invoice.assert_not_called()

    @pytest.mark.asyncio
    async def test_precheckout_check(self) -> None:
        self.telegram_pre_checkout_query.invoice_payload = self.INVOICE_PAYLOAD
        await self.sut.precheckout_check(self.telegram_update, self.telegram_context)
        self.telegram_pre_checkout_query.answer.assert_called_once_with(ok=True)

    @pytest.mark.asyncio
    async def test_precheckout_check_invalid_payload(self) -> None:
        self.telegram_pre_checkout_query.invoice_payload = "clearly_invalid_payload"
        await self.sut.precheckout_check(self.telegram_update, self.telegram_context)
        self.telegram_pre_checkout_query.answer.assert_called_once_with(
            ok=False, error_message="Something went wrong, try again"
        )

    @pytest.mark.asyncio
    async def test_successful_payment(self) -> None:
        await self.sut.successful_payment(self.telegram_update, self.telegram_context)
        self.telegram_update.effective_message.reply_text.assert_called_once()

    def _assert_keyboard_payment_callback_data(
        self, reply_markup: InlineKeyboardMarkup
    ) -> None:
        index = 0
        for keyboard_list in reply_markup.inline_keyboard:
            for keyboard in keyboard_list:
                data = keyboard.callback_data
                assert isinstance(data, PaymentData)
                assert data.value == self.PAYMENT_AMOUNTS[index]
                index += 1
            if index >= len(self.PAYMENT_AMOUNTS):
                break

        # Ensure that we've checked all payment amounts
        assert index == len(self.PAYMENT_AMOUNTS)
