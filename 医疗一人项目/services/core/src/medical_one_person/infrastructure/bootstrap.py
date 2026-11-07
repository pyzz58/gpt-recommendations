from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.infrastructure.db.models import User, Workspace


@dataclass(frozen=True)
class LocalIdentity:
    workspace_id: UUID
    owner_user_id: UUID


def bootstrap_local_owner(
    session_factory: sessionmaker[Session],
    *,
    workspace_name: str = "本地工作区",
    owner_name: str = "发起人",
    timezone_name: str = "Pacific/Auckland",
) -> LocalIdentity:
    with session_factory.begin() as session:
        workspace = session.scalar(select(Workspace).where(Workspace.name == workspace_name))
        if workspace is None:
            workspace = Workspace(
                id=uuid4(),
                name=workspace_name,
                timezone=timezone_name,
                created_at=datetime.now(UTC),
            )
            session.add(workspace)
            session.flush()
        owner = session.scalar(
            select(User).where(
                User.workspace_id == workspace.id,
                User.display_name == owner_name,
            )
        )
        if owner is None:
            owner = User(
                id=uuid4(),
                workspace_id=workspace.id,
                display_name=owner_name,
                is_owner=True,
                created_at=datetime.now(UTC),
            )
            session.add(owner)
            session.flush()
        return LocalIdentity(workspace_id=workspace.id, owner_user_id=owner.id)
