from unittest.mock import MagicMock

import pytest
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from pdf_bot.models import SupportData
from pdf_bot.payment import PaymentData, PaymentHandler, PaymentService
from tests.telegram_internal import TelegramTestMixin


class TestLanguageHandler(TelegramTestMixin):
    START_COMMAND = "start"
    SUPPORT_COMMAND = "support"

    def setup_method(self) -> None:
        super().setup_method()
        self.payment_service = MagicMock(spec=PaymentService)
        self.sut = PaymentHandler(self.payment_service)

    @pytest.mark.asyncio
    async def test_handlers(self) -> None:
        actual = self.sut.handlers
        assert len(actual) == 6

        handler_0 = actual[0]
        assert isinstance(handler_0, CommandHandler)
        assert handler_0.commands == {self.START_COMMAND}
        assert handler_0.filters.name == filters.Regex("support").name

        handler_1 = actual[1]
        assert isinstance(handler_1, CommandHandler)
        assert handler_1.commands == {self.SUPPORT_COMMAND}

        handler_2 = actual[2]
        assert isinstance(handler_2, CallbackQueryHandler)
        assert handler_2.pattern == SupportData

        handler_3 = actual[3]
        assert isinstance(handler_3, CallbackQueryHandler)
        assert handler_3.pattern == PaymentData

        handler_4 = actual[4]
        assert isinstance(handler_4, PreCheckoutQueryHandler)

        handler_5 = actual[5]
        assert isinstance(handler_5, MessageHandler)
        assert handler_5.filters == filters.SUCCESSFUL_PAYMENT

        for handler in actual:
            await handler.callback(self.telegram_update, self.telegram_context)

        assert self.payment_service.send_support_options.call_count == 3
        self.payment_service.precheckout_check.assert_called_once()
        self.payment_service.successful_payment.assert_called_once()
