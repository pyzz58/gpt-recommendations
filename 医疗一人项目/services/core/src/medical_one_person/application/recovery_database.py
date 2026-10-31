from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Date, DateTime, Numeric, Uuid, func, select
from sqlalchemy.orm import Session

from medical_one_person.infrastructure.db.base import Base
from medical_one_person.infrastructure.db.models import (
    BudgetLedgerEntry,
    Citation,
    KnowledgeChunk,
    TaskVersion,
)


def restore_manifest_rows(session: Session, manifest: dict[str, Any]) -> dict[str, int]:
    """Insert an already authenticated backup manifest into an empty migrated DB."""

    tables = manifest.get("tables")
    if not isinstance(tables, dict):
        raise ValueError("Backup table snapshot is missing")
    restored: dict[str, int] = {}
    for table in Base.metadata.sorted_tables:
        rows = tables.get(table.name)
        if rows is None:
            continue
        converted = [_convert_row(table, row) for row in rows]
        if converted:
            session.execute(table.insert(), converted)
        restored[table.name] = len(converted)
    expected = manifest.get("counts", {})
    if restored != {name: int(count) for name, count in expected.items()}:
        raise ValueError("Restored table counts do not match the backup manifest")
    verify_restored_relationships(session)
    return restored


def verify_restored_relationships(session: Session) -> None:
    orphan_citations = session.scalar(
        select(func.count())
        .select_from(Citation)
        .outerjoin(KnowledgeChunk, KnowledgeChunk.id == Citation.chunk_id)
        .where(KnowledgeChunk.id.is_(None))
    )
    if orphan_citations:
        raise ValueError("Restored citations reference missing chunks")
    orphan_versions = session.scalar(
        select(func.count())
        .select_from(TaskVersion)
        .where(TaskVersion.input_snapshot_sha256.is_(None))
    )
    if orphan_versions:
        raise ValueError("Restored task versions have no input snapshot hash")
    ledger_mismatch = session.scalar(
        select(func.count())
        .select_from(BudgetLedgerEntry)
        .where(BudgetLedgerEntry.ledger_key.is_(None))
    )
    if ledger_mismatch:
        raise ValueError("Restored budget ledger contains missing keys")


def _convert_row(table: Any, row: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for column in table.columns:
        if column.key not in row:
            continue
        value = row[column.key]
        column_type = column.type
        if value is not None and isinstance(column_type, Uuid):
            value = UUID(value)
        elif value is not None and isinstance(column_type, DateTime):
            value = datetime.fromisoformat(value)
        elif value is not None and isinstance(column_type, Date):
            value = date.fromisoformat(value)
        elif value is not None and isinstance(column_type, Numeric):
            value = Decimal(str(value))
        result[column.key] = value
    return result
