import os
from pathlib import Path

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


CRAWLER_DIR = Path(__file__).resolve().parent.parent


load_dotenv(
    CRAWLER_DIR / ".env"
)


DATABASE_URL = os.getenv(
    "DATABASE_URL"
)


if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not configured in crawler/.env"
    )



engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)



SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)



def get_session():

    session = SessionLocal()

    try:
        yield session

    finally:
        session.close()