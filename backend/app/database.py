import os
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_FILE)

DEFAULT_DATABASE_URL = "mysql+pymysql://root:password@localhost:3306/flipkart_clone"


def normalize_database_url(raw_url: str) -> str:
    database_url = raw_url.strip()
    if database_url.startswith("mysql://"):
        return database_url.replace("mysql://", "mysql+pymysql://", 1)
    return database_url


def build_database_url() -> str:
    for env_key in ("DATABASE_URL", "MYSQL_PUBLIC_URL", "MYSQL_URL"):
        raw_value = os.getenv(env_key)
        if raw_value:
            return normalize_database_url(raw_value)

    host = os.getenv("DB_HOST") or os.getenv("MYSQLHOST")
    port = os.getenv("DB_PORT") or os.getenv("MYSQLPORT") or "3306"
    user = os.getenv("DB_USER") or os.getenv("MYSQLUSER")
    password = os.getenv("DB_PASSWORD") or os.getenv("MYSQLPASSWORD") or ""
    database = os.getenv("DB_NAME") or os.getenv("MYSQLDATABASE")

    if host and user and database:
        return (
            "mysql+pymysql://"
            f"{quote(user, safe='')}:{quote(password, safe='')}"
            f"@{host}:{port}/{quote(database, safe='')}"
        )

    return DEFAULT_DATABASE_URL


DATABASE_URL = build_database_url()

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
