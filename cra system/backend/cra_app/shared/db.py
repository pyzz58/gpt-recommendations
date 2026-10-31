"""SQLAlchemy engine and session construction."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str, *, echo: bool = False) -> Engine:
    if not database_url.startswith("postgresql+psycopg://"):
        raise ValueError("CRA requires a PostgreSQL psycopg SQLAlchemy URL")
    return create_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=True,
    )


@contextmanager
def transactional_session(
    session_factory: sessionmaker[Session],
) -> Iterator[Session]:
    with session_factory() as session:
        with session.begin():
            yield session
