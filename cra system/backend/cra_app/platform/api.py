"""Health and truthful capability reporting."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter(tags=["platform"])


class LiveResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"
    service: str = "cra-system"


class DependencyState(BaseModel):
    status: Literal["ready", "unavailable"]
    detail: str | None = None


class ReadyResponse(BaseModel):
    status: Literal["ready", "unavailable"]
    dependencies: dict[str, DependencyState]


class ProviderCapability(BaseModel):
    provider: str
    status: Literal["not_configured", "configured"]
    validated: bool = False
    automatic_completion_allowed: bool = False
    limitation: str


class ModuleCapability(BaseModel):
    module_id: str
    label: str
    status: Literal[
        "implemented",
        "configured",
        "validated",
        "limited",
        "not_implemented",
    ]


class CapabilityResponse(BaseModel):
    schema_version: Literal[1] = 1
    environment: str
    generated_at: datetime
    identity_mode: Literal["synthetic", "oidc"]
    identity_configured: bool
    providers: dict[str, ProviderCapability]
    modules: list[ModuleCapability]
    automatic_completion_allowed: Literal[False] = False


@router.get("/health/live", response_model=LiveResponse)
def live() -> LiveResponse:
    return LiveResponse()


@router.get(
    "/health/ready",
    response_model=ReadyResponse,
    responses={503: {"description": "Database unavailable"}},
)
def ready(request: Request):
    try:
        with request.app.state.session_factory() as session:
            session.execute(text("SELECT 1"))
        body = ReadyResponse(
            status="ready",
            dependencies={"postgresql": DependencyState(status="ready")},
        )
        return body
    except (SQLAlchemyError, OSError):
        body = ReadyResponse(
            status="unavailable",
            dependencies={
                "postgresql": DependencyState(
                    status="unavailable", detail="database query failed"
                )
            },
        )
        return JSONResponse(
            status_code=503,
            content=body.model_dump(mode="json"),
        )


def _provider_capability(provider: str, capability: str) -> ProviderCapability:
    configured = provider.strip().lower() not in {"", "disabled", "none"}
    return ProviderCapability(
        provider=provider,
        status="configured" if configured else "not_configured",
        validated=False,
        automatic_completion_allowed=False,
        limitation=(
            "configured but not validated for clinical use"
            if configured
            else f"{capability} is unavailable until a provider is configured and validated"
        ),
    )


@router.get("/capabilities", response_model=CapabilityResponse)
def capabilities(request: Request) -> CapabilityResponse:
    settings = request.app.state.settings
    identity_provider = request.app.state.identity_provider
    return CapabilityResponse(
        environment=settings.environment,
        generated_at=datetime.now(UTC),
        identity_mode=identity_provider.mode,
        identity_configured=identity_provider.available,
        providers={
            "model": _provider_capability(settings.model_provider, "Model"),
            "ocr": _provider_capability(settings.ocr_provider, "OCR"),
            "rule_extractor": ProviderCapability(
                provider="anchored-rule-subset",
                status="configured",
                validated=True,
                automatic_completion_allowed=False,
                limitation=(
                    "validated on the synthetic W04 authored rule subset only; "
                    "free-form clinical protocols require review"
                ),
            ),
        },
        modules=[
            ModuleCapability(
                module_id="M01",
                label="项目与中心授权",
                status="implemented",
            ),
            ModuleCapability(
                module_id="M14",
                label="API与能力状态",
                status="implemented",
            ),
            ModuleCapability(
                module_id="M03",
                label="规则候选与分层list",
                status="implemented",
            ),
            ModuleCapability(
                module_id="M04",
                label="患者事实、访视时间线与断点",
                status="implemented",
            ),
            ModuleCapability(
                module_id="M05",
                label="受试者监查工作区",
                status="limited",
            ),
            ModuleCapability(
                module_id="M06",
                label="遗留问题、行动与Query跟进",
                status="implemented",
            ),
            ModuleCapability(
                module_id="M07",
                label="EDC Excel检验快照导入",
                status="implemented",
            ),
            ModuleCapability(
                module_id="M08",
                label="检验自动读取与核对",
                status="not_implemented",
            ),
            ModuleCapability(
                module_id="M11",
                label="报告与输出",
                status="not_implemented",
            ),
        ],
    )
