from dataclasses import dataclass


@dataclass
class PaymentData:
    message: str
    emoji: str
    value: int
