from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.project_views import WorkspaceReader
from medical_one_person.application.sessions import AuthenticatedPrincipal
from medical_one_person.domain.knowledge import SourceRecord, SourceSearchRequest
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import ExternalSourceSnapshot
from medical_one_person.infrastructure.sources.adapters import (
    SourceExecutionModeConflict,
    SourcePolicyViolation,
    SourceRouter,
    SourceUnavailableError,
)
from medical_one_person.infrastructure.sources.pubmed_http import (
    SourceRetrievalError,
    SourceRetrievalRateLimited,
)


class SourceSearchView(BaseModel):
    snapshot_id: UUID
    policy_id: str
    query: str
    adapter_ids: list[str]
    records: list[SourceRecord]
    record_count: int
    query_sha256: str
    result_sha256: str
    mode: str
    created_at: datetime


def build_source_search_router(
    *,
    session_factory: sessionmaker[Session],
    source_router: SourceRouter,
    project_reader: WorkspaceReader,
    current_principal: Callable[[Request], AuthenticatedPrincipal],
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/projects/{project_id}/sources",
        tags=["sources"],
    )

    @router.post(
        "/search",
        response_model=SourceSearchView,
        responses={
            400: {"description": "Unknown or prohibited source policy"},
            409: {"description": "Selected scholarly source adapters use mixed execution modes"},
            429: {"description": "Upstream scholarly source rate limit"},
            502: {"description": "Upstream scholarly source retrieval failure"},
            503: {"description": "No scholarly source adapter configured"},
        },
    )
    def search_sources(
        project_id: UUID,
        spec: SourceSearchRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> SourceSearchView:
        project_reader.get_project(
            actor_user_id=principal.user_id,
            project_id=project_id,
        )
        try:
            outcome = source_router.search_with_metadata(spec)
        except SourceExecutionModeConflict as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "SOURCE_EXECUTION_MODE_CONFLICT",
                    "message": str(exc),
                },
            ) from exc
        except SourceUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "SOURCE_ADAPTER_UNAVAILABLE",
                    "message": str(exc),
                },
            ) from exc
        except SourcePolicyViolation as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "SOURCE_POLICY_REJECTED",
                    "message": str(exc),
                },
            ) from exc
        except SourceRetrievalRateLimited as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "SOURCE_RATE_LIMITED",
                    "message": str(exc),
                },
            ) from exc
        except SourceRetrievalError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "SOURCE_RETRIEVAL_FAILED",
                    "message": str(exc),
                },
            ) from exc
        records = outcome.records
        now = datetime.now(UTC)
        query_hash = _sha256(spec.model_dump(mode="json"))
        record_payload = [record.model_dump(mode="json") for record in records]
        result_hash = _sha256(record_payload)
        snapshot_id = uuid4()
        with session_factory.begin() as session:
            set_rls_context(
                session,
                workspace_id=principal.workspace_id,
                user_id=principal.user_id,
            )
            session.add(
                ExternalSourceSnapshot(
                    id=snapshot_id,
                    workspace_id=principal.workspace_id,
                    project_id=project_id,
                    policy_id=spec.policy_id,
                    query=spec.query,
                    date_from=spec.date_from,
                    date_to=spec.date_to,
                    adapter_ids=list(outcome.adapter_ids),
                    records=record_payload,
                    record_count=len(record_payload),
                    query_sha256=query_hash,
                    result_sha256=result_hash,
                    mode=outcome.mode,
                    created_by_user_id=principal.user_id,
                    created_at=now,
                )
            )
        return SourceSearchView(
            snapshot_id=snapshot_id,
            policy_id=spec.policy_id,
            query=spec.query,
            adapter_ids=list(outcome.adapter_ids),
            records=records,
            record_count=len(records),
            query_sha256=query_hash,
            result_sha256=result_hash,
            mode=outcome.mode,
            created_at=now,
        )

    @router.get(
        "/snapshots/{snapshot_id}",
        response_model=SourceSearchView,
    )
    def read_snapshot(
        project_id: UUID,
        snapshot_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> SourceSearchView:
        project_reader.get_project(
            actor_user_id=principal.user_id,
            project_id=project_id,
        )
        with session_factory.begin() as session:
            set_rls_context(
                session,
                workspace_id=principal.workspace_id,
                user_id=principal.user_id,
            )
            snapshot = session.scalar(
                select(ExternalSourceSnapshot).where(
                    ExternalSourceSnapshot.id == snapshot_id,
                    ExternalSourceSnapshot.project_id == project_id,
                )
            )
            if snapshot is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "SOURCE_SNAPSHOT_NOT_FOUND"},
                )
            return SourceSearchView(
                snapshot_id=snapshot.id,
                policy_id=snapshot.policy_id,
                query=snapshot.query,
                adapter_ids=list(snapshot.adapter_ids),
                records=[
                    SourceRecord.model_validate(record)
                    for record in snapshot.records
                ],
                record_count=snapshot.record_count,
                query_sha256=snapshot.query_sha256,
                result_sha256=snapshot.result_sha256,
                mode=snapshot.mode,
                created_at=snapshot.created_at,
            )

    return router


def _sha256(value: object) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
