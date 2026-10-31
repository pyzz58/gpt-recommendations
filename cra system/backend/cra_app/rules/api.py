"""Authorized HTTP entry points for rule candidates, confirmation and use dates."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from cra_app.governance.api import (
    require_csrf,
    require_identity,
    scope_from_identity,
)
from cra_app.governance.identity import AuthenticatedIdentity
from cra_app.rules.contracts import (
    ConfirmRuleCommand,
    NodeEvaluation,
    RuleNode,
)
from cra_app.rules.service import (
    ApplicableRuleQuery,
    CreateActivationCommand,
    ExtractRuleCommand,
    PreviewActivationChangeCommand,
    RuleService,
)
from cra_app.shared.output_contract import OutputEnvelope

router = APIRouter(prefix="/api/v1", tags=["rules"])


class RuleVersionSummaryView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    rule_id: uuid.UUID
    snapshot_id: uuid.UUID
    version_no: int
    state: Literal["candidate", "confirmed", "withdrawn"]
    confirmation_basis: Literal[
        "candidate",
        "user_confirmation",
        "direct_rule_text",
        "unchanged_inheritance",
        "manual_add",
    ]
    semantic_status: Literal["complete", "analysis_required"]
    summary: str
    created_at: datetime
    confirmed_at: datetime | None


class RuleListItemView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    rule_key: str
    policy_layer: Literal["common", "study", "site"]
    title: str
    status: Literal["candidate", "active", "withdrawn"]
    revision: int
    current_version: RuleVersionSummaryView | None
    candidate_versions: list[RuleVersionSummaryView]


class RuleSourceRefView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    anchor_id: uuid.UUID
    quote: str
    locator: str | None
    ordinal: int


class RuleRelationView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    from_version_id: uuid.UUID | None
    to_version_id: uuid.UUID
    relation_type: str
    reason: str
    evidence: list[dict[str, Any]]


class RuleVersionDetailView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: uuid.UUID
    rule_key: str
    policy_layer: Literal["common", "study", "site"]
    rule_revision: int
    version: RuleVersionSummaryView
    tree: RuleNode
    source_refs: list[RuleSourceRefView]
    relations: list[RuleRelationView]


class ExtractionResponse(BaseModel):
    snapshot_id: uuid.UUID
    document_version_id: uuid.UUID
    status: Literal["ready", "needs_review", "invalid"]
    rule_version_ids: list[uuid.UUID]
    replayed: bool
    duplicate_source: bool
    candidate_count: int
    confirmed_count: int


class ConfirmationResponse(BaseModel):
    rule_id: uuid.UUID
    rule_version_id: uuid.UUID
    revision: int
    replayed: bool


class ActivationResponse(BaseModel):
    activation_id: uuid.UUID
    revision: int
    conflicts: list[str]
    replayed: bool


class ActivationWindowView(BaseModel):
    starts_on: date
    ends_before: date | None
    reason: str | None = None


class ActivationChangePreviewView(BaseModel):
    activation_id: uuid.UUID
    current: ActivationWindowView
    proposed: ActivationWindowView
    contains_start: bool
    conflicting_activation_ids: list[uuid.UUID]
    affected_rule_ids: list[uuid.UUID]
    affected_rule_version_ids: list[uuid.UUID]
    retroactive_reassessment: Literal[False] = False


class RuleExtractionCoverageView(BaseModel):
    unit_key: str
    status: Literal[
        "processed",
        "background",
        "analysis_required",
        "unsupported",
        "failed",
    ]
    reason: str | None
    anchor_id: uuid.UUID | None


class ApplicableRuleView(BaseModel):
    rule_id: uuid.UUID
    rule_key: str
    rule_version_id: uuid.UUID
    activation_id: uuid.UUID
    tree: RuleNode
    evaluation: NodeEvaluation


class ApplicabilityResponse(BaseModel):
    envelope: OutputEnvelope
    rules: list[ApplicableRuleView]
    common_policy_configured: bool


class ConfirmRuleRequest(ConfirmRuleCommand):
    pass


def _service(request: Request) -> RuleService:
    return request.app.state.rule_service


def _summary(item: Any) -> RuleVersionSummaryView:
    version = item
    return RuleVersionSummaryView(
        id=version.id,
        rule_id=version.rule_id,
        snapshot_id=version.snapshot_id,
        version_no=version.version_no,
        state=version.state,
        confirmation_basis=version.confirmation_basis,
        semantic_status=version.semantic_status,
        summary=str(version.tree["summary"]),
        created_at=version.created_at,
        confirmed_at=version.confirmed_at,
    )


@router.post(
    "/document-versions/{document_version_id}/rule-candidates",
    response_model=ExtractionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
def extract_rule_candidates(
    document_version_id: uuid.UUID,
    command: ExtractRuleCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ExtractionResponse:
    outcome = _service(request).extract_candidates(
        scope_from_identity(identity), document_version_id, command
    )
    return ExtractionResponse(
        snapshot_id=outcome.snapshot_id,
        document_version_id=outcome.document_version_id,
        status=outcome.status,
        rule_version_ids=list(outcome.rule_version_ids),
        replayed=outcome.replayed,
        duplicate_source=outcome.duplicate_source,
        candidate_count=outcome.candidate_count,
        confirmed_count=outcome.confirmed_count,
    )


@router.get(
    "/studies/{study_id}/rules",
    response_model=list[RuleListItemView],
)
def list_rules(
    study_id: uuid.UUID,
    request: Request,
    site_id: uuid.UUID | None = Query(default=None),
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[RuleListItemView]:
    items = _service(request).list_rules(
        scope_from_identity(identity), study_id, site_id
    )
    return [
        RuleListItemView(
            id=item.rule.id,
            rule_key=item.rule.rule_key,
            policy_layer=item.rule.policy_layer,
            title=item.rule.title,
            status=item.rule.status,
            revision=item.rule.revision,
            current_version=(
                _summary(item.current_version)
                if item.current_version is not None
                else None
            ),
            candidate_versions=[
                _summary(version) for version in item.candidate_versions
            ],
        )
        for item in items
    ]


@router.get(
    "/rules/{rule_id}/versions",
    response_model=list[RuleVersionSummaryView],
)
def list_rule_versions(
    rule_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[RuleVersionSummaryView]:
    return [
        _summary(version)
        for version in _service(request).list_rule_versions(
            scope_from_identity(identity), rule_id
        )
    ]


@router.get(
    "/rule-versions/{rule_version_id}",
    response_model=RuleVersionDetailView,
)
def get_rule_version(
    rule_version_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> RuleVersionDetailView:
    item = _service(request).get_rule_version(
        scope_from_identity(identity), rule_version_id
    )
    return RuleVersionDetailView(
        rule_id=item.rule.id,
        rule_key=item.rule.rule_key,
        policy_layer=item.rule.policy_layer,
        rule_revision=item.rule.revision,
        version=_summary(item.version),
        tree=item.tree,
        source_refs=[
            RuleSourceRefView(
                id=ref.id,
                anchor_id=ref.anchor_id,
                quote=ref.quote,
                locator=ref.locator,
                ordinal=ref.ordinal,
            )
            for ref in item.source_refs
        ],
        relations=[
            RuleRelationView(
                id=relation.id,
                from_version_id=relation.from_version_id,
                to_version_id=relation.to_version_id,
                relation_type=relation.relation_type,
                reason=relation.reason,
                evidence=relation.evidence,
            )
            for relation in item.relations
        ],
    )


@router.post(
    "/rules/{rule_id}/confirmation",
    response_model=ConfirmationResponse,
    dependencies=[Depends(require_csrf)],
)
def confirm_rule(
    rule_id: uuid.UUID,
    command: ConfirmRuleRequest,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ConfirmationResponse:
    outcome = _service(request).confirm_rule(
        scope_from_identity(identity), rule_id, command
    )
    return ConfirmationResponse(
        rule_id=outcome.rule_id,
        rule_version_id=outcome.rule_version_id,
        revision=outcome.revision,
        replayed=outcome.replayed,
    )


@router.post(
    "/version-activations",
    response_model=ActivationResponse,
    dependencies=[Depends(require_csrf)],
)
def create_version_activation(
    command: CreateActivationCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ActivationResponse:
    outcome = _service(request).create_activation(
        scope_from_identity(identity), command
    )
    return ActivationResponse(
        activation_id=outcome.activation_id,
        revision=outcome.revision,
        conflicts=list(outcome.conflicts),
        replayed=outcome.replayed,
    )


@router.post(
    "/version-activations/{activation_id}/preview-change",
    response_model=ActivationChangePreviewView,
)
def preview_version_activation_change(
    activation_id: uuid.UUID,
    command: PreviewActivationChangeCommand,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ActivationChangePreviewView:
    return ActivationChangePreviewView.model_validate(
        _service(request).preview_activation_change(
            scope_from_identity(identity), activation_id, command
        )
    )


@router.get(
    "/rule-snapshots/{snapshot_id}/coverage",
    response_model=list[RuleExtractionCoverageView],
)
def rule_extraction_coverage(
    snapshot_id: uuid.UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> list[RuleExtractionCoverageView]:
    return [
        RuleExtractionCoverageView(
            unit_key=item.unit_key,
            status=item.status,
            reason=item.reason,
            anchor_id=item.anchor_id,
        )
        for item in _service(request).list_extraction_coverage(
            scope_from_identity(identity), snapshot_id
        )
    ]


@router.post(
    "/rules/applicable",
    response_model=ApplicabilityResponse,
)
def applicable_rules(
    query: ApplicableRuleQuery,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
) -> ApplicabilityResponse:
    service = _service(request)
    outcome = service.applicable_rules(scope_from_identity(identity), query)
    return ApplicabilityResponse(
        envelope=outcome.envelope,
        rules=[
            ApplicableRuleView(
                rule_id=item.rule.id,
                rule_key=item.rule.rule_key,
                rule_version_id=item.version.id,
                activation_id=item.activation_id,
                tree=item.tree,
                evaluation=item.evaluation,
            )
            for item in outcome.rules
        ],
        common_policy_configured=service.common_policy_set is not None,
    )
