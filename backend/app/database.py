from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()


def _engine_url() -> str:
    url = settings.database_url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and "+psycopg" not in url and "+psycopg2" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


url = _engine_url()
connect_args: dict = {}
engine_kwargs: dict = {"pool_pre_ping": True}

if url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    # Transaction pooler (6543) cannot reuse prepared statements.
    connect_args = {"prepare_threshold": None}
    if "sslmode=" not in url:
        connect_args["sslmode"] = "require"

if ":6543" in url:
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 0

engine = create_engine(url, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_schema() -> None:
    """Add columns create_all will not add on an existing database."""
    sqlite_adds = [
        ("knowledge_docs", "embedding", "JSON"),
        ("users", "stripe_customer_id", "VARCHAR(255) DEFAULT ''"),
        ("users", "card_last4", "VARCHAR(4) DEFAULT ''"),
        ("users", "card_brand", "VARCHAR(32) DEFAULT ''"),
        ("users", "password_reset_token_hash", "VARCHAR(64) DEFAULT ''"),
        ("users", "password_reset_expires", "DATETIME"),
        ("interview_sessions", "mode", "VARCHAR(32) DEFAULT 'text'"),
        ("profiles", "linkedin_url", "VARCHAR(500) DEFAULT ''"),
        ("profiles", "github_username", "VARCHAR(120) DEFAULT ''"),
    ]
    pg_adds = [
        "ALTER TABLE knowledge_docs ADD COLUMN IF NOT EXISTS embedding jsonb",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255) DEFAULT ''",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS card_last4 VARCHAR(4) DEFAULT ''",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS card_brand VARCHAR(32) DEFAULT ''",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_token_hash VARCHAR(64) DEFAULT ''",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_expires TIMESTAMPTZ",
        "ALTER TABLE interview_sessions ADD COLUMN IF NOT EXISTS mode VARCHAR(32) DEFAULT 'text'",
        "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS linkedin_url VARCHAR(500) DEFAULT ''",
        "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS github_username VARCHAR(120) DEFAULT ''",
    ]
    with engine.begin() as conn:
        if settings.is_postgres:
            for stmt in pg_adds:
                conn.execute(text(stmt))
            return
        for table, column, spec in sqlite_adds:
            try:
                rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            except Exception:
                continue
            names = {r[1] for r in rows}
            if rows and column not in names:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {spec}"))
