from pydantic import BaseModel
from typing import List
from datetime import datetime, date


class PaymentItem(BaseModel):
    method: str
    amount: float


class ExpenseCreate(BaseModel):
    supplier_id: int
    total_amount: float
    date: date
    payment_date: date | None = None
    payment_status: str = "pending"
    payments: List[PaymentItem]


class CajaTotalResponse(BaseModel):
    date: str
    total_amount: float