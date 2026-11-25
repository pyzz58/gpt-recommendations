from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import NotFoundError
from medical_one_person.domain.artifacts import (
    ArtifactMode,
    ArtifactOrigin,
    ArtifactVersionRecord,
)
from medical_one_person.infrastructure.artifacts import LocalArtifactStore
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    Artifact,
    ArtifactVersion,
    Project,
    ProjectEvent,
    User,
)


class ArtifactService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        store: LocalArtifactStore,
    ) -> None:
        self._session_factory = session_factory
        self._store = store

    def create_version(
        self,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        title: str,
        media_type: str,
        content: bytes,
        mode: ArtifactMode,
        origin: ArtifactOrigin,
        producer: str,
    ) -> ArtifactVersionRecord:
        self._ensure_access(project_id, actor_user_id)
        stored = self._store.put(content)
        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            actor = session.get(User, actor_user_id)
            if actor is None:
                raise NotFoundError("Project not found")
            set_rls_context(
                session,
                workspace_id=actor.workspace_id,
                user_id=actor.id,
            )
            project = session.scalar(
                select(Project).where(Project.id == project_id).with_for_update()
            )
            if project is None or project.workspace_id != actor.workspace_id:
                raise NotFoundError("Project not found")

            artifact = session.scalar(
                select(Artifact).where(
                    Artifact.project_id == project_id,
                    Artifact.title == title,
                )
            )
            if artifact is None:
                artifact = Artifact(
                    id=uuid4(),
                    workspace_id=project.workspace_id,
                    project_id=project.id,
                    title=title,
                    created_by_user_id=actor.id,
                    created_at=now,
                )
                session.add(artifact)
                session.flush()

            current_version = session.scalar(
                select(func.max(ArtifactVersion.version)).where(
                    ArtifactVersion.artifact_id == artifact.id
                )
            )
            version = ArtifactVersion(
                id=uuid4(),
                project_id=project.id,
                artifact_id=artifact.id,
                version=(current_version or 0) + 1,
                media_type=media_type,
                object_key=stored.object_key,
                sha256=stored.sha256,
                size_bytes=stored.size_bytes,
                mode=mode.value,
                raw_or_derived=origin.value,
                producer=producer,
                created_at=now,
            )
            session.add(version)
            session.flush()

            last_event_sequence = session.scalar(
                select(ProjectEvent.project_seq)
                .where(ProjectEvent.project_id == project.id)
                .order_by(ProjectEvent.project_seq.desc())
                .limit(1)
            )
            session.add(
                ProjectEvent(
                    id=uuid4(),
                    workspace_id=project.workspace_id,
                    project_id=project.id,
                    project_seq=(last_event_sequence or 0) + 1,
                    type="artifact.version_created",
                    actor_user_id=actor.id,
                    object_type="artifact_version",
                    object_id=version.id,
                    object_revision=version.version,
                    payload={
                        "artifact_id": str(artifact.id),
                        "sha256": version.sha256,
                        "media_type": version.media_type,
                        "mode": version.mode,
                        "raw_or_derived": version.raw_or_derived,
                    },
                    correlation_id=uuid4(),
                    created_at=now,
                )
            )
            return ArtifactVersionRecord(
                id=version.id,
                project_id=version.project_id,
                artifact_id=version.artifact_id,
                version=version.version,
                object_key=version.object_key,
                sha256=version.sha256,
                size_bytes=version.size_bytes,
                mode=ArtifactMode(version.mode),
            )

    def _ensure_access(self, project_id: UUID, actor_user_id: UUID) -> None:
        with self._session_factory() as session:
            actor = session.get(User, actor_user_id)
            if actor is None:
                raise NotFoundError("Project not found")
            set_rls_context(
                session,
                workspace_id=actor.workspace_id,
                user_id=actor.id,
            )
            project = session.get(Project, project_id)
            if project is None or project.workspace_id != actor.workspace_id:
                raise NotFoundError("Project not found")
