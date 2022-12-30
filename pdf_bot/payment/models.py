from pydantic import BaseModel


class PaymentData(BaseModel):
    label: str
    emoji: str
    value: int
