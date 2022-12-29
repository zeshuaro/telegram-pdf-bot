from pydantic import BaseModel


class SupportData:
    ...


class PaymentData(BaseModel):
    label: str
    emoji: str
    value: int
