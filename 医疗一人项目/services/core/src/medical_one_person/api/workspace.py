from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import AgentRoleConfig
from medical_one_person.application.opportunities import (
    OpportunityRecord,
    OpportunityService,
)
from medical_one_person.application.project_views import (
    AgentSceneView,
    EventView,
    ProjectListItem,
    ProjectOverview,
    TaskView,
    WorkspaceReader,
)
from medical_one_person.application.projects import ProjectService
from medical_one_person.application.sessions import AuthenticatedPrincipal
from medical_one_person.domain.opportunities import (
    OpportunityCard,
    OpportunityStatus,
)
from medical_one_person.domain.projects import ProjectSnapshot


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    scope: str = Field(min_length=1, max_length=10_000)


class OpportunityCreateRequest(BaseModel):
    card: OpportunityCard


class OpportunitySelectionRequest(BaseModel):
    expected_revision: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=10_000)
    scope: str = Field(min_length=1, max_length=10_000)
    evidence_version_ids: list[str] = Field(default_factory=list)


class OpportunityView(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    status: OpportunityStatus
    current_version: int
    revision: int
    card: OpportunityCard


class SelectionView(BaseModel):
    decision_id: UUID
    opportunity_id: UUID
    opportunity_version: int
    status: OpportunityStatus


def build_workspace_router(
    session_factory: sessionmaker[Session],
    roles: dict[str, AgentRoleConfig],
    current_principal: Callable[[Request], AuthenticatedPrincipal],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["workspace"])
    projects = ProjectService(session_factory)
    opportunities = OpportunityService(session_factory)
    reader = WorkspaceReader(session_factory, roles)

    @router.get("/projects", response_model=list[ProjectListItem])
    def list_projects(
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[ProjectListItem]:
        return reader.list_projects(actor_user_id=principal.user_id)

    @router.post("/projects", response_model=ProjectSnapshot, status_code=201)
    def create_project(
        request: ProjectCreateRequest,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> ProjectSnapshot:
        return projects.create_project(
            actor_user_id=principal.user_id,
            name=request.name,
            scope=request.scope,
            idempotency_key=idempotency_key,
        )

    @router.get("/projects/{project_id}", response_model=ProjectSnapshot)
    def get_project(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> ProjectSnapshot:
        return reader.get_project(
            actor_user_id=principal.user_id,
            project_id=project_id,
        )

    @router.get("/projects/{project_id}/overview", response_model=ProjectOverview)
    def project_overview(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> ProjectOverview:
        return reader.overview(
            actor_user_id=principal.user_id,
            project_id=project_id,
        )

    @router.get("/projects/{project_id}/tasks", response_model=list[TaskView])
    def project_tasks(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[TaskView]:
        return reader.list_tasks(
            actor_user_id=principal.user_id,
            project_id=project_id,
        )

    @router.get("/projects/{project_id}/agents", response_model=list[AgentSceneView])
    def project_agents(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[AgentSceneView]:
        return reader.list_agents(
            actor_user_id=principal.user_id,
            project_id=project_id,
        )

    @router.get("/projects/{project_id}/events", response_model=list[EventView])
    def project_events(
        project_id: UUID,
        after: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[EventView]:
        return reader.events(
            actor_user_id=principal.user_id,
            project_id=project_id,
            after=after,
            limit=limit,
        )

    @router.get("/projects/{project_id}/events/stream")
    def project_event_stream(
        request: Request,
        project_id: UUID,
        after: int = Query(default=0, ge=0),
        last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> StreamingResponse:
        cursor = after
        if last_event_id:
            try:
                cursor = max(cursor, int(last_event_id))
            except ValueError as exc:
                raise ValueError("Last-Event-ID must be a project sequence") from exc

        async def events() -> AsyncIterator[str]:
            nonlocal cursor
            yield "retry: 3000\n\n"
            while not await request.is_disconnected():
                rows = await asyncio.to_thread(
                    reader.events,
                    actor_user_id=principal.user_id,
                    project_id=project_id,
                    after=cursor,
                    limit=100,
                )
                if not rows:
                    yield ": heartbeat\n\n"
                for row in rows:
                    cursor = max(cursor, row.project_seq)
                    payload = json.dumps(
                        row.model_dump(mode="json"),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    yield (f"id: {row.project_seq}\nevent: project-event\ndata: {payload}\n\n")
                await asyncio.sleep(1)

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @router.get(
        "/projects/{project_id}/opportunities",
        response_model=list[OpportunityView],
    )
    def project_opportunities(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[OpportunityView]:
        return [
            _opportunity_view(item)
            for item in opportunities.compare(
                workspace_id=principal.workspace_id,
                actor_user_id=principal.user_id,
                project_id=project_id,
            )
        ]

    @router.post(
        "/projects/{project_id}/opportunities",
        response_model=OpportunityView,
        status_code=201,
    )
    def create_opportunity(
        project_id: UUID,
        request: OpportunityCreateRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> OpportunityView:
        return _opportunity_view(
            opportunities.create(
                project_id=project_id,
                actor_user_id=principal.user_id,
                card=request.card,
            )
        )

    @router.post(
        "/projects/{project_id}/opportunities/{opportunity_id}/select",
        response_model=SelectionView,
    )
    def select_opportunity(
        project_id: UUID,
        opportunity_id: UUID,
        request: OpportunitySelectionRequest,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> SelectionView:
        result = opportunities.select_opportunity(
            workspace_id=principal.workspace_id,
            actor_user_id=principal.user_id,
            project_id=project_id,
            opportunity_id=opportunity_id,
            expected_revision=request.expected_revision,
            reason=request.reason,
            scope=request.scope,
            evidence_version_ids=request.evidence_version_ids,
            idempotency_key=idempotency_key,
        )
        return SelectionView(
            decision_id=result.decision_id,
            opportunity_id=result.opportunity_id,
            opportunity_version=result.opportunity_version,
            status=result.status,
        )

    return router


def _opportunity_view(record: OpportunityRecord) -> OpportunityView:
    return OpportunityView(
        id=record.id,
        project_id=record.project_id,
        title=record.title,
        status=record.status,
        current_version=record.current_version,
        revision=record.revision,
        card=record.card,
    )
