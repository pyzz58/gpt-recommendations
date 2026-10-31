from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


def set_rls_context(session: Session, *, workspace_id: UUID, user_id: UUID | None) -> None:
    """Set transaction-local identity values used by PostgreSQL RLS policies."""

    session.execute(
        text(
            """
            SELECT
              set_config('medical_one.workspace_id', :workspace_id, true),
              set_config('medical_one.user_id', :user_id, true)
            """
        ),
        {
            "workspace_id": str(workspace_id),
            "user_id": str(user_id) if user_id is not None else "",
        },
    )
