"""Memory helpers: history window, facts, users."""
from __future__ import annotations

from sqlalchemy import delete, select

from bot.db.models import Fact, Message, User, session_factory


async def get_or_create_user(telegram_id: int, username: str = "") -> User:
    """Fetch the user row, creating it if needed."""
    factory = session_factory()
    async with factory() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            user = User(telegram_id=telegram_id, username=username)
            session.add(user)
            await session.commit()
        return user


async def save_user(user: User) -> None:
    """Persist user changes."""
    factory = session_factory()
    async with factory() as session:
        session.add(user)
        await session.commit()


async def add_message(telegram_id: int, role: str, content: str, limit: int = 30) -> None:
    """Append a history message and trim to the last ``limit`` rows."""
    factory = session_factory()
    async with factory() as session:
        session.add(Message(telegram_id=telegram_id, role=role, content=content))
        await session.commit()
        ids = (
            await session.scalars(
                select(Message.id)
                .where(Message.telegram_id == telegram_id)
                .order_by(Message.id.desc())
                .offset(limit)
            )
        ).all()
        if ids:
            await session.execute(delete(Message).where(Message.id.in_(ids)))
            await session.commit()


async def get_history(telegram_id: int, limit: int = 30) -> list[dict[str, str]]:
    """Return the last ``limit`` messages as role/content dicts (oldest first)."""
    factory = session_factory()
    async with factory() as session:
        rows = (
            await session.scalars(
                select(Message)
                .where(Message.telegram_id == telegram_id)
                .order_by(Message.id.desc())
                .limit(limit)
            )
        ).all()
    return [{"role": m.role, "content": m.content} for m in reversed(rows)]


async def clear_history(telegram_id: int) -> None:
    """Delete all history for a user."""
    factory = session_factory()
    async with factory() as session:
        await session.execute(delete(Message).where(Message.telegram_id == telegram_id))
        await session.commit()


async def get_facts(telegram_id: int) -> dict[str, str]:
    """Return all learned facts for a user."""
    factory = session_factory()
    async with factory() as session:
        rows = (
            await session.scalars(select(Fact).where(Fact.telegram_id == telegram_id))
        ).all()
    return {f.key: f.value for f in rows}


async def save_fact(telegram_id: int, key: str, value: str) -> None:
    """Insert or update a learned fact."""
    factory = session_factory()
    async with factory() as session:
        existing = await session.scalar(
            select(Fact).where(Fact.telegram_id == telegram_id, Fact.key == key)
        )
        if existing:
            existing.value = value
        else:
            session.add(Fact(telegram_id=telegram_id, key=key, value=value))
        await session.commit()


async def clear_facts(telegram_id: int) -> None:
    """Delete all learned facts for a user."""
    factory = session_factory()
    async with factory() as session:
        await session.execute(delete(Fact).where(Fact.telegram_id == telegram_id))
        await session.commit()
