import logging
from pathlib import Path


CRAWLER_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = CRAWLER_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "crawler.log"

logger = logging.getLogger("crawler")
logger.setLevel(logging.INFO)
logger.propagate = False


if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.ERROR)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(threadName)s | %(message)s")

    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)