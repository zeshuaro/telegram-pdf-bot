from telegram.ext import (
    BaseHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from pdf_bot.telegram_handler import AbstractTelegramHandler

from .models import PaymentData, SupportData
from .payment_service import PaymentService


class PaymentHandler(AbstractTelegramHandler):
    _START_COMMAND = "start"
    _SUPPORT_COMMAND = "support"

    def __init__(self, payment_service: PaymentService) -> None:
        self.payment_service = payment_service

    @property
    def handlers(self) -> list[BaseHandler]:
        return [
            CommandHandler(
                self._START_COMMAND,
                self.payment_service.send_support_options,
                filters.Regex("support"),
            ),
            CommandHandler(
                self._SUPPORT_COMMAND, self.payment_service.send_support_options
            ),
            CallbackQueryHandler(
                self.payment_service.send_support_options, pattern=SupportData
            ),
            CallbackQueryHandler(
                self.payment_service.send_invoice, pattern=PaymentData
            ),
            PreCheckoutQueryHandler(self.payment_service.precheckout_check),
            MessageHandler(
                filters.SUCCESSFUL_PAYMENT, self.payment_service.successful_payment
            ),
        ]
