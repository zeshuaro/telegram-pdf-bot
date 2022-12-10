import re

from telegram import InlineKeyboardMarkup

from pdf_bot.payment import PaymentService
from tests.language import LanguageServiceTestMixin
from tests.telegram_internal import TelegramTestMixin


class TestFeedbackService(LanguageServiceTestMixin, TelegramTestMixin):
    INVOICE_PAYLOAD = "invoice_payload"
    CURRENCY = "USD"
    KEYBOARD_SIZE = 2

    PAYMENT_AMOUNTS = [1, 3, 5, 10]

    def setup_method(self) -> None:
        super().setup_method()
        self.language_service = self.mock_language_service()
        self.sut = PaymentService(self.language_service)

    def test_send_support_options(self) -> None:
        self.sut.send_support_options(self.telegram_update, self.telegram_context)

        args, kwargs = self.telegram_bot.send_message.call_args
        assert args[0] == self.telegram_user_id

        reply_markup: InlineKeyboardMarkup | None = kwargs.get("reply_markup")
        assert reply_markup is not None
        self._assert_keyboard_payment_callback_data(reply_markup)

    def test_send_support_options_with_query(self) -> None:
        self.sut.send_support_options(
            self.telegram_update, self.telegram_context, self.telegram_callback_query
        )

        args, kwargs = self.telegram_bot.send_message.call_args
        assert args[0] == self.telegram_query_user_id

        reply_markup: InlineKeyboardMarkup | None = kwargs.get("reply_markup")
        assert reply_markup is not None
        self._assert_keyboard_payment_callback_data(reply_markup)

    def test_send_invoice(self) -> None:
        self.telegram_callback_query.data = "payment,message,1"
        self.sut.send_invoice(
            self.telegram_update, self.telegram_context, self.telegram_callback_query
        )
        self.telegram_context.bot.send_invoice.assert_called_once()

    def test_precheckout_check(self) -> None:
        self.telegram_pre_checkout_query.invoice_payload = self.INVOICE_PAYLOAD
        self.sut.precheckout_check(self.telegram_update, self.telegram_context)
        self.telegram_pre_checkout_query.answer.assert_called_once_with(ok=True)

    def test_precheckout_check_invalid_payload(self) -> None:
        self.telegram_pre_checkout_query.invoice_payload = "clearly_invalid_payload"
        self.sut.precheckout_check(self.telegram_update, self.telegram_context)
        self.telegram_pre_checkout_query.answer.assert_called_once_with(
            ok=False, error_message="Something went wrong, try again"
        )

    def test_successful_payment(self) -> None:
        self.sut.successful_payment(self.telegram_update, self.telegram_context)
        self.telegram_update.effective_message.reply_text.assert_called_once()

    def _assert_keyboard_payment_callback_data(
        self, reply_markup: InlineKeyboardMarkup
    ) -> None:
        index = 0
        for keyboard_list in reply_markup.inline_keyboard:
            for keyboard in keyboard_list:
                data: str = keyboard.callback_data
                assert (
                    re.match(
                        f"payment,.*,{self.PAYMENT_AMOUNTS[index]}",
                        data,
                    )
                    is not None
                )
                index += 1
            if index >= len(self.PAYMENT_AMOUNTS):
                break

        # Ensure that we've checked all payment amounts
        assert index == len(self.PAYMENT_AMOUNTS)
