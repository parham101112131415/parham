"""Async SQLite database via SQLAlchemy. All runtime data lives under DATA_DIR."""
from __future__ import annotations

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    """Declarative base for all models."""


class User(Base):
    """Per-user profile built during onboarding (/start) and editable via /reconfig."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(128), default="")
    real_name: Mapped[str] = mapped_column(String(128), default="")
    bot_name: Mapped[str] = mapped_column(String(128), default="")
    personality: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str] = mapped_column(String(128), default="")
    interests: Mapped[str] = mapped_column(Text, default="")
    mode: Mapped[str] = mapped_column(String(32), default="normal")
    lang: Mapped[str] = mapped_column(String(16), default="auto")
    onboarded: Mapped[bool] = mapped_column(default=False)


class Message(Base):
    """Rolling chat history (last N messages per user)."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)


class Fact(Base):
    """Long-term facts learned about the user ([MEMORY: key=value])."""

    __tablename__ = "facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    key: Mapped[str] = mapped_column(String(128))
    value: Mapped[str] = mapped_column(Text)


class Feedback(Base):
    """👍/👎 feedback used to tune tone."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    message_id: Mapped[int] = mapped_column(BigInteger, default=0)
    kind: Mapped[str] = mapped_column(String(16))  # "like" | "dislike"


_engine = None
_session_factory = None


def init_engine(db_path: str) -> None:
    """Create the async engine for the given SQLite path."""
    global _engine, _session_factory
    _engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables if they do not exist."""
    assert _engine is not None, "init_engine() must be called first"
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def session_factory() -> async_sessionmaker:
    """Return the active session factory."""
    assert _session_factory is not None, "init_engine() must be called first"
    return _session_factory
