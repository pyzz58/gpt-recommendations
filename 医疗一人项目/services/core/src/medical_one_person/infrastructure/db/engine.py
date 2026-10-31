from __future__ import annotations

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from medical_one_person.contracts import DependencyStatus

EXPECTED_DATABASE_REVISION = "d9a7e3f1b420"


def create_database_engine(database_url: str) -> Engine:
    return create_engine(
        database_url,
        connect_args={"connect_timeout": 2},
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_recycle=1800,
    )


def database_status(engine: Engine) -> DependencyStatus:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
        if revision != EXPECTED_DATABASE_REVISION:
            return DependencyStatus(
                status="unavailable",
                detail="PostgreSQL schema migration is missing or out of date",
            )
        return DependencyStatus(
            status="ready",
            detail=f"PostgreSQL connected at migration {EXPECTED_DATABASE_REVISION}",
        )
    except SQLAlchemyError:
        return DependencyStatus(
            status="unavailable",
            detail="PostgreSQL is unavailable or its schema has not been migrated",
        )
