from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from shared.db_base import Base
from config import DATABASE_URL

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
