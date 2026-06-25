import logging

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _run_migrations():
    """Run schema migrations for existing tables.
    SQLAlchemy's create_all() doesn't alter existing tables,
    so we add missing columns manually."""
    if not settings.database_url.startswith("sqlite"):
        return

    migrations = [
        # v0.2: add route column to conversation_logs
        "ALTER TABLE conversation_logs ADD COLUMN route VARCHAR(10) DEFAULT 'RAG' NOT NULL",
        # v0.3: add store column to documents
        "ALTER TABLE documents ADD COLUMN store VARCHAR(10) DEFAULT 'vector' NOT NULL",
        # v0.4: add user_id column to conversation_logs
        "ALTER TABLE conversation_logs ADD COLUMN user_id INTEGER DEFAULT 0",
        # v0.4b: backfill existing rows — if all user_id=0, set to 1 (first admin)
        "UPDATE conversation_logs SET user_id = 1 WHERE user_id = 0",
        # v0.5: add nl2sql_prompt and nl2sql_sql columns to conversation_logs
        "ALTER TABLE conversation_logs ADD COLUMN nl2sql_prompt TEXT",
        "ALTER TABLE conversation_logs ADD COLUMN nl2sql_sql TEXT",
        # v0.6: add session_title to conversation_logs
        "ALTER TABLE conversation_logs ADD COLUMN session_title VARCHAR(200)",
    ]

    from sqlalchemy import inspect
    inspector = inspect(engine)
    existing_columns = {}
    for table_name in inspector.get_table_names():
        existing_columns[table_name] = {c["name"] for c in inspector.get_columns(table_name)}

    for sql in migrations:
        if sql.strip().upper().startswith("ALTER TABLE"):
            # Parse table name and column name from ALTER TABLE statement
            table_name = sql.split("ALTER TABLE ")[1].split(" ")[0]
            col_name = sql.split("ADD COLUMN ")[1].split(" ")[0]
            if table_name in existing_columns and col_name not in existing_columns[table_name]:
                try:
                    with engine.connect() as conn:
                        conn.execute(text(sql))
                        conn.commit()
                        logger.info("Migration applied: %s", sql[:80])
                except Exception as e:
                    logger.warning("Migration failed (may already exist): %s", e)
        else:
            # Non-ALTER (e.g. UPDATE) — always run idempotently
            try:
                with engine.connect() as conn:
                    result = conn.execute(text(sql))
                    conn.commit()
                    logger.info("Migration applied: %s (rows=%s)", sql[:80], result.rowcount)
            except Exception as e:
                logger.warning("Migration failed: %s", e)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _run_migrations()
