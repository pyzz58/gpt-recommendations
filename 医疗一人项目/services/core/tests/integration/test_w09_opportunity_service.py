from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import (
    ConflictingOperationError,
    NotFoundError,
    RevisionConflictError,
)
from medical_one_person.application.knowledge import ClaimService
from medical_one_person.application.opportunities import OpportunityService
from medical_one_person.application.projects import ProjectService
from medical_one_person.domain.opportunities import (
    OpportunityCard,
    OpportunityStatus,
    ScientificBrief,
)
from medical_one_person.infrastructure.bootstrap import (
    LocalIdentity,
    bootstrap_local_owner,
)
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    Decision,
    ProjectEvent,
    ScientificBriefRecord,
    User,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_PATH = PROJECT_ROOT / "fixtures" / "opportunity-contract-examples.json"


def _fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _cards() -> list[OpportunityCard]:
    return [OpportunityCard.model_validate(item) for item in _fixture()["opportunities"]]


def _setup(
    session_factory: sessionmaker[Session],
) -> tuple[LocalIdentity, Any, OpportunityService, list[Any]]:
    identity = bootstrap_local_owner(session_factory)
    project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="W09 合成机会比较",
        scope="验证候选结构、用户选择和科学简报，不代表任何真实研发判断。",
        idempotency_key="w09-create-project",
    )
    service = OpportunityService(session_factory)
    records = [
        service.create(
            project_id=project.id,
            actor_user_id=identity.owner_user_id,
            card=card,
        )
        for card in _cards()
    ]
    return identity, project, service, records


def test_three_track_comparison_and_owner_selection_are_replay_safe(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project, service, records = _setup(session_factory)
    compared = service.compare(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
    )
    assert [item.card.track.value for item in compared] == [
        "device",
        "ivd",
        "pet_repurposing",
    ]
    assert {item.status for item in compared} == {OpportunityStatus.PROPOSED}

    non_owner_id = uuid4()
    with session_factory.begin() as session:
        session.add(
            User(
                id=non_owner_id,
                workspace_id=identity.workspace_id,
                display_name="W09 非负责人",
                is_owner=False,
                created_at=datetime.now(UTC),
            )
        )
    selected = records[0]
    with pytest.raises(PermissionError, match="verified workspace owner"):
        service.select_opportunity(
            workspace_id=identity.workspace_id,
            actor_user_id=non_owner_id,
            project_id=project.id,
            opportunity_id=selected.id,
            expected_revision=selected.revision,
            reason="无权选择",
            scope="W09 合成场景",
            evidence_version_ids=[],
            idempotency_key="w09-non-owner",
        )

    with pytest.raises(NotFoundError, match="Evidence version not found"):
        service.select_opportunity(
            workspace_id=identity.workspace_id,
            actor_user_id=identity.owner_user_id,
            project_id=project.id,
            opportunity_id=selected.id,
            expected_revision=selected.revision,
            reason="使用不存在的证据",
            scope="W09 合成场景",
            evidence_version_ids=[str(uuid4())],
            idempotency_key="w09-missing-evidence",
        )

    claim = ClaimService(session_factory).create(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        statement="合成断言只用于验证证据版本归属。",
        directness="unknown",
    )
    other_project = ProjectService(session_factory).create_project(
        actor_user_id=identity.owner_user_id,
        name="W09 另一项目",
        scope="验证证据版本不能跨项目引用。",
        idempotency_key="w09-create-other-project",
    )
    other_claim = ClaimService(session_factory).create(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=other_project.id,
        statement="另一个项目的合成断言。",
        directness="unknown",
    )
    with pytest.raises(NotFoundError, match="Evidence version not found"):
        service.select_opportunity(
            workspace_id=identity.workspace_id,
            actor_user_id=identity.owner_user_id,
            project_id=project.id,
            opportunity_id=selected.id,
            expected_revision=selected.revision,
            reason="尝试引用另一项目证据",
            scope="W09 合成场景",
            evidence_version_ids=[str(other_claim.version_id)],
            idempotency_key="w09-cross-project-evidence",
        )
    with pytest.raises(RevisionConflictError):
        service.select_opportunity(
            workspace_id=identity.workspace_id,
            actor_user_id=identity.owner_user_id,
            project_id=project.id,
            opportunity_id=selected.id,
            expected_revision=selected.revision + 1,
            reason="版本已变化",
            scope="W09 合成场景",
            evidence_version_ids=[str(claim.version_id)],
            idempotency_key="w09-stale-revision",
        )

    arguments = {
        "workspace_id": identity.workspace_id,
        "actor_user_id": identity.owner_user_id,
        "project_id": project.id,
        "opportunity_id": selected.id,
        "expected_revision": selected.revision,
        "reason": "合成选择理由，仅用于验证合同。",
        "scope": "只进入桌面核查，不授权外部动作。",
        "evidence_version_ids": [str(claim.version_id)],
        "idempotency_key": "w09-owner-selection",
    }
    result = service.select_opportunity(**arguments)
    replay = service.select_opportunity(**arguments)
    assert replay == result
    assert result.status == OpportunityStatus.SELECTED
    assert result.opportunity_version == selected.current_version

    with pytest.raises(ConflictingOperationError):
        service.select_opportunity(
            **{
                **arguments,
                "reason": "同一幂等键下改写了理由。",
            }
        )

    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        decision = session.scalar(select(Decision))
        events = session.scalars(select(ProjectEvent).order_by(ProjectEvent.project_seq)).all()
    assert decision is not None
    assert decision.selected_opportunity_id == selected.id
    assert decision.evidence_version_ids == [str(claim.version_id)]
    assert events[-1].type == "opportunity.selected"


def test_opportunity_revisions_and_scientific_brief_versions_are_preserved(
    session_factory: sessionmaker[Session],
) -> None:
    identity, project, service, records = _setup(session_factory)
    opportunity = records[1]
    revised_card = _cards()[1].model_copy(update={"title": "合成样例：修订后的 IVD"})

    with pytest.raises(RevisionConflictError):
        service.revise(
            opportunity_id=opportunity.id,
            actor_user_id=identity.owner_user_id,
            expected_revision=2,
            card=revised_card,
            status=OpportunityStatus.UNDER_REVIEW,
        )

    revised = service.revise(
        opportunity_id=opportunity.id,
        actor_user_id=identity.owner_user_id,
        expected_revision=opportunity.revision,
        card=revised_card,
        status=OpportunityStatus.UNDER_REVIEW,
    )
    assert revised.current_version == 2
    assert revised.revision == 2
    assert revised.card.title == revised_card.title

    brief = ScientificBrief.model_validate(_fixture()["scientific_brief"])
    first_id = service.create_scientific_brief(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        brief=brief,
    )
    second_id = service.create_scientific_brief(
        workspace_id=identity.workspace_id,
        actor_user_id=identity.owner_user_id,
        project_id=project.id,
        brief=brief.model_copy(update={"key_unknowns": ["修订后的合成未知项"]}),
    )
    with session_factory.begin() as session:
        set_rls_context(
            session,
            workspace_id=identity.workspace_id,
            user_id=identity.owner_user_id,
        )
        stored = session.scalars(
            select(ScientificBriefRecord).order_by(ScientificBriefRecord.brief_version)
        ).all()
        brief_events = session.scalar(
            select(func.count())
            .select_from(ProjectEvent)
            .where(ProjectEvent.type == "scientific_brief.created")
        )
    assert [item.id for item in stored] == [first_id, second_id]
    assert [item.brief_version for item in stored] == [1, 2]
    assert stored[1].content["key_unknowns"] == ["修订后的合成未知项"]
    assert brief_events == 2


def test_w09_tables_are_forced_through_workspace_rls(database: Engine) -> None:
    with database.connect() as connection:
        policies = connection.scalar(
            text("SELECT count(*) FROM pg_policies WHERE schemaname = 'public'")
        )
        tables = connection.execute(
            text(
                """
                SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname IN (
                    'scientific_briefs',
                    'opportunities',
                    'opportunity_versions',
                    'decisions'
                  )
                ORDER BY c.relname
                """
            )
        ).all()
    assert policies == 85
    assert len(tables) == 4
    assert all(row.relrowsecurity and row.relforcerowsecurity for row in tables)
