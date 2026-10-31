from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.agents.config import AgentRoleConfig
from medical_one_person.application.plan_execution import (
    MockPlanExecutor,
    PlanExecutionView,
)
from medical_one_person.application.plans import (
    PlanDispatchView,
    PlanService,
    PlanView,
    TaskReviewView,
)
from medical_one_person.application.sessions import AuthenticatedPrincipal
from medical_one_person.domain.plans import PlanSpec, ReviewDecision, ReviewFinding
from medical_one_person.infrastructure.workflows import WorkflowRegistry


class PlanCreateRequest(BaseModel):
    source_decision_id: UUID
    spec: PlanSpec


class PlanRevisionRequest(BaseModel):
    expected_revision: int = Field(ge=1)


class PlanStateRequest(PlanRevisionRequest):
    reason: str = Field(min_length=1, max_length=4_000)


class PlanResumeRequest(PlanRevisionRequest):
    additional_rework_rounds: int = Field(default=0, ge=0, le=10)


class PlanExecuteRequest(BaseModel):
    max_tasks: int = Field(default=4, ge=1, le=10)


class TaskReviewRequest(PlanRevisionRequest):
    plan_id: UUID
    reviewer_role: str = Field(pattern=r"^A(25|26)$")
    decision: ReviewDecision
    summary: str = Field(min_length=1, max_length=10_000)
    findings: list[ReviewFinding] = Field(default_factory=list)


def build_plan_router(
    session_factory: sessionmaker[Session],
    roles: dict[str, AgentRoleConfig],
    workflows: WorkflowRegistry,
    theory_hash: str,
    current_principal: Callable[[Request], AuthenticatedPrincipal],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/projects/{project_id}", tags=["plans"])
    service = PlanService(session_factory, roles, workflows)
    executor = MockPlanExecutor(
        session_factory,
        roles,
        theory_hash=theory_hash,
    )

    @router.get("/plans", response_model=list[PlanView])
    def list_plans(
        project_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[PlanView]:
        return service.list_plans(
            project_id=project_id,
            actor_user_id=principal.user_id,
        )

    @router.post("/plans", response_model=PlanView, status_code=201)
    def submit_plan(
        project_id: UUID,
        request: PlanCreateRequest,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> PlanView:
        return service.submit_plan(
            project_id=project_id,
            actor_user_id=principal.user_id,
            source_decision_id=request.source_decision_id,
            spec=request.spec,
            idempotency_key=idempotency_key,
        )

    @router.get("/plans/{plan_id}", response_model=PlanView)
    def get_plan(
        project_id: UUID,
        plan_id: UUID,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> PlanView:
        return service.get_plan(
            project_id=project_id,
            plan_id=plan_id,
            actor_user_id=principal.user_id,
        )

    @router.post("/plans/{plan_id}/activate", response_model=PlanView)
    def activate_plan(
        project_id: UUID,
        plan_id: UUID,
        request: PlanRevisionRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> PlanView:
        return service.activate_plan(
            project_id=project_id,
            plan_id=plan_id,
            actor_user_id=principal.user_id,
            expected_revision=request.expected_revision,
        )

    @router.post("/plans/{plan_id}/dispatch", response_model=PlanDispatchView)
    def dispatch_plan(
        project_id: UUID,
        plan_id: UUID,
        request: PlanRevisionRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> PlanDispatchView:
        return service.dispatch_plan(
            project_id=project_id,
            plan_id=plan_id,
            actor_user_id=principal.user_id,
            expected_revision=request.expected_revision,
        )

    @router.post("/plans/{plan_id}/execute", response_model=PlanExecutionView)
    def execute_plan(
        project_id: UUID,
        plan_id: UUID,
        request: PlanExecuteRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> PlanExecutionView:
        return executor.execute_ready(
            project_id=project_id,
            plan_id=plan_id,
            actor_user_id=principal.user_id,
            max_tasks=request.max_tasks,
        )

    @router.post("/plans/{plan_id}/pause", response_model=PlanView)
    def pause_plan(
        project_id: UUID,
        plan_id: UUID,
        request: PlanStateRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> PlanView:
        return service.pause_plan(
            project_id=project_id,
            plan_id=plan_id,
            actor_user_id=principal.user_id,
            expected_revision=request.expected_revision,
            reason=request.reason,
        )

    @router.post("/plans/{plan_id}/resume", response_model=PlanView)
    def resume_plan(
        project_id: UUID,
        plan_id: UUID,
        request: PlanResumeRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> PlanView:
        return service.resume_plan(
            project_id=project_id,
            plan_id=plan_id,
            actor_user_id=principal.user_id,
            expected_revision=request.expected_revision,
            additional_rework_rounds=request.additional_rework_rounds,
        )

    @router.post("/plans/{plan_id}/stop", response_model=PlanView)
    def stop_plan(
        project_id: UUID,
        plan_id: UUID,
        request: PlanStateRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> PlanView:
        return service.stop_plan(
            project_id=project_id,
            plan_id=plan_id,
            actor_user_id=principal.user_id,
            expected_revision=request.expected_revision,
            reason=request.reason,
        )

    @router.post("/tasks/{task_id}/review", response_model=TaskReviewView)
    def review_task(
        project_id: UUID,
        task_id: UUID,
        request: TaskReviewRequest,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=1),
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> TaskReviewView:
        return service.review_task(
            project_id=project_id,
            plan_id=request.plan_id,
            task_id=task_id,
            actor_user_id=principal.user_id,
            expected_revision=request.expected_revision,
            reviewer_role=request.reviewer_role,
            decision=request.decision,
            summary=request.summary,
            findings=request.findings,
            idempotency_key=idempotency_key,
        )

    return router
