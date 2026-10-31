"""Business jobs, transactional outbox and Procrastinate queue adapter."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

import psycopg
from procrastinate import App, SyncPsycopgConnector
from procrastinate.exceptions import AlreadyEnqueued
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from cra_app.shared.db import Base


def digest_payload(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class BusinessJob(Base):
    __tablename__ = "business_jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "study_id", "input_version_id"],
            [
                "document_versions.tenant_id",
                "document_versions.study_id",
                "document_versions.id",
            ],
            name="fk_business_jobs_input_version",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "actor_id",
            "tenant_id",
            "scope_fingerprint",
            "job_type",
            "idempotency_key",
            name="uq_business_jobs_idempotency",
        ),
        CheckConstraint(
            "job_type IN ('parse_document')",
            name="ck_business_jobs_type",
        ),
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed','cancelled')",
            name="ck_business_jobs_status",
        ),
        CheckConstraint("attempts >= 0", name="ck_business_jobs_attempts"),
        CheckConstraint(
            "max_attempts >= 1 AND attempts <= max_attempts",
            name="ck_business_jobs_max_attempts",
        ),
        Index(
            "ix_business_jobs_status_available",
            "status",
            "available_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    authentication_source: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    platform_roles: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    scope_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    input_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    output: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        UniqueConstraint("dedup_key", name="uq_outbox_events_dedup"),
        CheckConstraint(
            "status IN ('pending','published','failed')",
            name="ck_outbox_events_status",
        ),
        Index("ix_outbox_events_status_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ProcrastinateQueue:
    """Thin queue adapter; business state remains in BusinessJob/OutboxEvent."""

    TASK_NAME = "cra.document.parse"

    def __init__(self, database_url: str):
        self._conninfo = database_url.replace(
            "postgresql+psycopg://", "postgresql://"
        )
        self._schema_ready = False

    def _new_app(self) -> App:
        return App(connector=SyncPsycopgConnector(conninfo=self._conninfo))

    def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        with psycopg.connect(self._conninfo) as connection:
            exists = connection.execute(
                "SELECT to_regclass('public.procrastinate_jobs') IS NOT NULL"
            ).fetchone()
        if exists and exists[0]:
            self._schema_ready = True
            return
        app = self._new_app()
        app.open()
        try:
            app.schema_manager.apply_schema()
        finally:
            app.close()
        self._schema_ready = True

    def enqueue_parse(self, job_id: uuid.UUID) -> int | None:
        self.ensure_schema()
        app = self._new_app()
        app.open()
        try:
            try:
                deferred = app.configure_task(
                    self.TASK_NAME,
                    allow_unknown=True,
                    queue="documents",
                    retry=2,
                    queueing_lock=f"document-parse:{job_id}",
                ).defer(
                    job_id=str(job_id),
                )
                return getattr(deferred, "job_id", deferred)
            except AlreadyEnqueued:
                return None
        finally:
            app.close()


def relay_pending_outbox(
    session_factory: sessionmaker[Session],
    queue: ProcrastinateQueue,
    *,
    limit: int = 20,
) -> int:
    """Relay pending outbox rows. Queueing locks make retries idempotent."""
    published = 0
    with session_factory() as session:
        with session.begin():
            events = list(
                session.scalars(
                    select(OutboxEvent)
                    .where(OutboxEvent.status == "pending")
                    .order_by(OutboxEvent.created_at)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            )
            for event in events:
                event.attempts += 1
                try:
                    if event.event_type != "document.parse.requested":
                        raise ValueError("unsupported outbox event")
                    job_id = uuid.UUID(str(event.payload["job_id"]))
                    queue.enqueue_parse(job_id)
                    event.status = "published"
                    event.published_at = datetime.now(UTC)
                    event.last_error = None
                    published += 1
                except Exception as exc:
                    event.last_error = type(exc).__name__
                    if event.attempts >= 5:
                        event.status = "failed"
    return published
