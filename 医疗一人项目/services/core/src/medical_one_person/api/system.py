from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, HTTPException, status

from medical_one_person.config import Settings
from medical_one_person.contracts import (
    CapabilityReport,
    DependencyStatus,
    HealthReport,
    MockSmokeRequest,
    MockSmokeResponse,
    ProviderCapability,
)
from medical_one_person.domain.recovery import NetworkMode
from medical_one_person.providers import FakeModelProvider


def build_system_router(
    settings: Settings,
    database_checker: Callable[[], DependencyStatus],
    agent_status: DependencyStatus,
    skill_status: DependencyStatus,
    source_status: DependencyStatus,
    *,
    storage_checker: Callable[[], DependencyStatus] | None = None,
    queue_checker: Callable[[], DependencyStatus] | None = None,
    worker_checker: Callable[[], DependencyStatus] | None = None,
) -> APIRouter:
    router = APIRouter()
    fake_provider = FakeModelProvider()

    def checked(
        checker: Callable[[], DependencyStatus] | None,
        detail: str,
    ) -> DependencyStatus:
        if checker is None:
            return DependencyStatus(status="not_checked", detail=detail)
        try:
            return checker()
        except Exception:
            return DependencyStatus(
                status="unavailable",
                detail="Runtime dependency check raised an unexpected error",
            )

    @router.get("/health/live", response_model=HealthReport, tags=["system"])
    def live() -> HealthReport:
        return HealthReport(
            status="ok",
            mode=settings.app_mode,
            checks={"process": DependencyStatus(status="ready", detail="API process is running")},
        )

    @router.get("/health/ready", response_model=HealthReport, tags=["system"])
    def ready() -> HealthReport:
        database = database_checker()
        storage = checked(
            storage_checker,
            "Storage readiness is not injected in this process",
        )
        queue = checked(
            queue_checker,
            "Queue schema readiness is not injected in this process",
        )
        worker = checked(
            worker_checker,
            "Worker heartbeat readiness is not injected in this process",
        )
        provider_ready = settings.app_mode == "mock"
        is_ready = (
            provider_ready
            and all(
                dependency.status == "ready"
                for dependency in (database, storage, queue, worker)
            )
        )
        return HealthReport(
            status="ok" if is_ready else "not_ready",
            mode=settings.app_mode,
            checks={
                "process": DependencyStatus(status="ready", detail="API process is running"),
                "mock_provider": DependencyStatus(
                    status="ready" if provider_ready else "not_configured",
                    detail="Deterministic network-free adapter"
                    if settings.app_mode == "mock"
                    else "Live model provider is not configured",
                ),
                "database": database,
                "artifact_storage": storage,
                "queue": queue,
                "worker": worker,
            },
        )

    @router.get(
        "/api/v1/system/capabilities",
        response_model=CapabilityReport,
        tags=["system"],
    )
    def capabilities() -> CapabilityReport:
        database = database_checker()
        storage = checked(storage_checker, "Storage check is unavailable")
        queue = checked(queue_checker, "Queue schema check is unavailable")
        worker = checked(worker_checker, "Worker heartbeat check is unavailable")
        provider_status: Literal["ready", "not_configured"] = (
            "ready" if settings.app_mode == "mock" else "not_configured"
        )
        provider_detail = (
            "Deterministic mock responses only"
            if settings.app_mode == "mock"
            else "Configure a reviewed provider adapter before using live mode"
        )
        return CapabilityReport(
            mode=settings.app_mode,
            label="本地开发链" if settings.app_mode == "mock" else "live 模式",
            implementation_scope=(
                "PostgreSQL持久化、项目RLS、可靠调度、26岗合同、独立运行上下文、"
                "检索证据、机会选择、版本化DAG、三领域流程、数据版本/统计、"
                "项目/知识页面、Office/PDF导出、授权模拟邮件、独立规则审计、"
                "知识回收站和加密备份恢复校验"
            ),
            providers=[
                ProviderCapability(
                    provider_id=fake_provider.provider_id,
                    mode="mock",
                    status=provider_status,
                    detail=provider_detail,
                )
            ],
            dependencies={
                "database": database,
                "worker": worker,
                "queue": queue,
                "artifact_storage": storage,
                "tool_isolation": DependencyStatus(
                    status="not_checked",
                    detail=(
                        "Native authorization gateway/audit is available; "
                        "container policy exists, but the runtime sandbox remains unverified"
                    ),
                ),
                "agents": agent_status,
                "skills": skill_status,
                "sources": source_status,
                "network": DependencyStatus(
                    status="ready",
                    detail=(
                        "Offline mode blocks remote tools; local database, files, "
                        "parsing, search and mock workflows remain available"
                        if settings.network_mode == NetworkMode.OFFLINE
                        else (
                            "Allowlisted network mode is configured; live adapters still "
                            "require their own credentials and validation"
                        )
                    ),
                ),
                "knowledge": DependencyStatus(
                    status="ready",
                    detail=(
                        "Project-scoped knowledge browsing, chunked upload, parsing, "
                        "lexical search snapshots, citations and version impact are connected"
                    ),
                ),
                "opportunities": DependencyStatus(
                    status="ready",
                    detail=(
                        "Versioned opportunity cards, scientific briefs and owner-only "
                        "selection contracts are connected to the opportunity browser"
                    ),
                ),
                "project_interface": DependencyStatus(
                    status="ready",
                    detail=(
                        "Local HttpOnly session, project browser, task/agent scenes, "
                        "knowledge upload and project event SSE are implemented"
                    ),
                ),
                "planning": DependencyStatus(
                    status="ready",
                    detail=(
                        "Versioned bounded DAGs, dispatch, mock execution, independent-profile "
                        "review records, rework, pause/resume and iteration limits are implemented"
                    ),
                ),
                "domain_workflows": DependencyStatus(
                    status="ready",
                    detail=(
                        "Pet repurposing, IVD and device workflow packages define stages, "
                        "required roles, criteria, failure routes and external gates"
                    ),
                ),
                "datasets": DependencyStatus(
                    status="ready",
                    detail=(
                        "Immutable raw table versions, cleaning derivations, "
                        "pre-specified deterministic analyses, charts and review records "
                        "are implemented"
                    ),
                ),
                "external_records": DependencyStatus(
                    status="ready",
                    detail=(
                        "Organizations, contacts, experts, engagement scopes, quotes, "
                        "contract states, deliverables, professional records and explicit "
                        "external authorizations are connected to project PostgreSQL state"
                    ),
                ),
                "audit_reviews": DependencyStatus(
                    status="ready",
                    detail=(
                        "Deterministic A25/A26 rule reviews, immutable input snapshots, "
                        "blocking and synthetic evaluation are available; these are not "
                        "human or non-mock independent-agent reviews"
                    ),
                ),
                "recovery": DependencyStatus(
                    status="ready",
                    detail=(
                        "Knowledge trash/restore, safe index rebuild for uncited versions, "
                        "AES-256-GCM project backups and isolated restore verification "
                        "are available; active database overwrite is not enabled"
                    ),
                ),
            },
            external_actions=DependencyStatus(
                status="ready",
                detail=(
                    "The local mock mailbox records drafts, explicit authorization, "
                    "simulated delivery and uncertain outcomes; real email, purchases, "
                    "contracts, and experiments remain disabled; W16 records are local "
                    "evidence entries and do not contact providers"
                ),
            ),
            limitations=[
                "W13—W15 are not a complete scientific workflow; deterministic statistics "
                "do not prove data quality, valid study design or scientific interpretation; "
                "Office and mock-mail checks do not establish content validity, and review "
                "records are not W17 independent review.",
                "Mock output is not scientific evidence or professional review.",
                "Synthetic opportunity fixtures do not establish demand, probability, "
                "cost, rights, efficacy, or safety.",
                "No real model, inbox, provider credential, or external institution is connected; "
                "mock mail cannot establish that an external person replied or agreed.",
                "W17 rule audits are deterministic defect checks, not human experts or "
                "non-mock independent agents.",
                "W18 restore checks verify an encrypted archive in an isolated directory; "
                "they do not replace the active database and do not prove off-site backup.",
            ],
        )

    @router.post(
        "/api/v1/system/mock-smoke",
        response_model=MockSmokeResponse,
        tags=["system"],
    )
    def mock_smoke(request: MockSmokeRequest) -> MockSmokeResponse:
        if settings.app_mode != "mock":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "MOCK_DISABLED",
                    "message": "The mock smoke endpoint is disabled outside mock mode.",
                },
            )
        return fake_provider.smoke(request.input)

    return router
