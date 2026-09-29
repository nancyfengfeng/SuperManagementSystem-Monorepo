# utils/time.py

from datetime import datetime
from zoneinfo import ZoneInfo

CR_TZ = ZoneInfo("America/Costa_Rica")

def cr_today():
    return datetime.now(CR_TZ).date()