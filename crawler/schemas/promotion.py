from dataclasses import dataclass
from datetime import datetime


@dataclass
class PromotionItem:

    quantity: int

    total_price: float

    start_time: datetime | None

    end_time: datetime | None