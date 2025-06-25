# database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "sqlite+aiosqlite:///./chatbot.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Set to True for debugging, False for production
    future=True,  # Use future mode for SQLAlchemy 2.0 compatibility
    connect_args={"check_same_thread": False}  # Required for SQLite with async
)

SessionLocal = async_sessionmaker(
    autocommit=False, # Do not autocommit transactions, use explicit commits(commit is when changes are saved to the database)
    autoflush=False, # Do not autoflush changes automatically, use explicit flushes(flush is when changes are sent to the database)
    bind=engine,
    future=True  # Use future mode for SQLAlchemy 2.0 compatibility
)

class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass