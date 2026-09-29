from pydantic import BaseModel
from datetime import date
from typing import List


class IncomeTypeItem(BaseModel):
    income_type: str
    amount: float


class IncomeCreate(BaseModel):
    date: date
    total_amount: float
    types: List[IncomeTypeItem]