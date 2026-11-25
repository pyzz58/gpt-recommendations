from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from medical_one_person.application.errors import NotFoundError
from medical_one_person.infrastructure.db.context import set_rls_context
from medical_one_person.infrastructure.db.models import (
    Conversation,
    Message,
    Project,
    ProjectEvent,
    User,
)


@dataclass(frozen=True)
class MessageRecord:
    id: UUID
    conversation_id: UUID
    project_id: UUID
    speaker: str
    content: str
    source_kind: str
    created_at: datetime


class ConversationService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, *, project_id: UUID, actor_user_id: UUID, title: str) -> Conversation:
        with self._session_factory.begin() as session:
            project, actor = self._project_and_actor(session, project_id, actor_user_id)
            conversation = Conversation(
                id=uuid4(),
                workspace_id=project.workspace_id,
                project_id=project.id,
                owner_user_id=actor.id,
                title=title,
                created_at=datetime.now(UTC),
            )
            session.add(conversation)
            session.flush()
            return conversation

    def append_message(
        self,
        *,
        project_id: UUID,
        conversation_id: UUID,
        actor_user_id: UUID,
        speaker: str,
        content: str,
        source_kind: str,
    ) -> MessageRecord:
        if speaker not in {"user", "agent", "system"}:
            raise ValueError("Unsupported message speaker")
        if not content.strip():
            raise ValueError("Message content cannot be empty")

        now = datetime.now(UTC)
        with self._session_factory.begin() as session:
            project, actor = self._project_and_actor(session, project_id, actor_user_id)
            session.scalar(select(Project).where(Project.id == project.id).with_for_update())
            conversation = session.get(Conversation, conversation_id)
            if conversation is None or conversation.project_id != project.id:
                raise NotFoundError("Conversation not found")
            message = Message(
                id=uuid4(),
                project_id=project.id,
                conversation_id=conversation.id,
                speaker=speaker,
                content=content,
                source_kind=source_kind,
                created_at=now,
            )
            session.add(message)
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
                    type="conversation.message_created",
                    actor_user_id=actor.id,
                    object_type="message",
                    object_id=message.id,
                    object_revision=1,
                    payload={
                        "conversation_id": str(conversation.id),
                        "speaker": speaker,
                        "source_kind": source_kind,
                    },
                    correlation_id=uuid4(),
                    created_at=now,
                )
            )
            return MessageRecord(
                id=message.id,
                conversation_id=message.conversation_id,
                project_id=message.project_id,
                speaker=message.speaker,
                content=message.content,
                source_kind=message.source_kind,
                created_at=message.created_at,
            )

    @staticmethod
    def _project_and_actor(
        session: Session, project_id: UUID, actor_user_id: UUID
    ) -> tuple[Project, User]:
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
        return project, actor
