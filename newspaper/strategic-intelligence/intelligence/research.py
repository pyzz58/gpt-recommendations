"""W16 shared research revision and atomic commit boundary.

This module binds research outputs to one exact revision and commits a set of
outputs together. It does not judge content, adopt an artifact or authorize
publication. Parent-version checks use the shared Archive's immediate SQLite
write transaction, so a stale holder cannot overwrite a newer revision.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import AwareDatetime, model_validator

from .archive import Archive, ArchiveError, Conflict, canonical
from .contracts import (Contract, Digest, Identifier, NonBlank, ObjectKind, ReferenceUse,
                        Representation, RightsGrant, SourceTimes, StoredVersion,
                        VersionReference, VersionSubmission)


class ResearchRole(str, Enum):
    DRAFT = "DRAFT"
    ADVISER = "ADVISER"
    TEACHER = "TEACHER"
    CONDITIONS = "CONDITIONS"
    REVIEW = "REVIEW"


class ResearchRevision(Contract):
    schema_version: Literal[1] = 1
    revision_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    based_on_revision_id: Identifier | None = None
    input_version_ids: tuple[Identifier, ...] = ()
    reason: NonBlank
    created_at: AwareDatetime

    @model_validator(mode="after")
    def unique_inputs(self) -> Self:
        if len(self.input_version_ids) != len(set(self.input_version_ids)):
            raise ValueError("Duplicate research revision input")
        if self.revision_id == self.based_on_revision_id:
            raise ValueError("A revision cannot be based on itself")
        return self


class ArtifactLink(Contract):
    schema_version: Literal[1] = 1
    link_id: Identifier
    theme_id: Identifier
    revision_id: Identifier
    artifact_version_id: Identifier
    role: ResearchRole
    created_at: AwareDatetime

    @model_validator(mode="after")
    def distinct_versions(self) -> Self:
        if self.link_id == self.artifact_version_id:
            raise ValueError("Artifact and link IDs must differ")
        return self


class ResearchCommitRequest(Contract):
    schema_version: Literal[1] = 1
    commit_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    revision_id: Identifier
    link_ids: tuple[Identifier, ...]
    expected_commit_id: Identifier | None = None
    created_at: AwareDatetime

    @model_validator(mode="after")
    def complete_set(self) -> Self:
        if len(self.link_ids) < 2 or len(self.link_ids) != len(set(self.link_ids)):
            raise ValueError("A research commit needs at least two unique output links")
        return self


class ArtifactBinding(Contract):
    link_id: Identifier
    artifact_version_id: Identifier
    role: ResearchRole


class ResearchCommit(Contract):
    schema_version: Literal[1] = 1
    commit_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    revision_id: Identifier
    expected_commit_id: Identifier | None
    artifacts: tuple[ArtifactBinding, ...]
    created_at: AwareDatetime

    @model_validator(mode="after")
    def unique_bindings(self) -> Self:
        links = [item.link_id for item in self.artifacts]
        artifacts = [item.artifact_version_id for item in self.artifacts]
        roles = [item.role for item in self.artifacts]
        if len(links) != len(set(links)):
            raise ValueError("Duplicate artifact link")
        if len(artifacts) != len(set(artifacts)):
            raise ValueError("Duplicate artifact version")
        if len(roles) != len(set(roles)):
            raise ValueError("One commit cannot assign one role to multiple outputs")
        return self


class ResearchError(ArchiveError):
    """A revision/commit boundary failure, not a content or publishing decision."""


class ResearchRevisionController:
    def __init__(self, archive: Archive, rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError("ResearchRevisionController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError("ResearchRevisionController requires an internal journal grant")
        self.archive = archive
        self.rights = rights

    @staticmethod
    def _revision_object(theme_id: str) -> str:
        return f"REV-{theme_id}"

    @staticmethod
    def _commit_object(theme_id: str) -> str:
        return f"COMMIT-{theme_id}"

    @staticmethod
    def _link_object(theme_id: str, link_id: str) -> str:
        return f"LINK-{theme_id}-{link_id}"

    def append_revision(self, revision: ResearchRevision,
                        expected_parent_id: str | None) -> StoredVersion:
        if not isinstance(revision, ResearchRevision):
            raise TypeError("append_revision requires a ResearchRevision")
        revision = ResearchRevision.model_validate_json(revision.model_dump_json(warnings=False))
        if revision.based_on_revision_id != expected_parent_id:
            raise ResearchError("Revision parent and expected parent differ")
        latest = self.archive.latest(self._revision_object(revision.theme_id))
        actual_parent = latest.submission.version_id if latest else None
        if actual_parent != expected_parent_id:
            raise Conflict("Research revision is stale")
        for version_id in revision.input_version_ids:
            self.archive.get(version_id)
        references = tuple(VersionReference(target_version_id=version_id, use=ReferenceUse.SUPPORT,
                                            locator=f"revision input {index}")
                           for index, version_id in enumerate(revision.input_version_ids))
        submission = VersionSubmission(
            schema_version=2, object_id=self._revision_object(revision.theme_id),
            kind=ObjectKind.RESEARCH_REVISION, version_id=revision.revision_id,
            parent_version_id=expected_parent_id,
            title=f"{revision.theme_id} research revision", spec_sha256=revision.spec_sha256,
            created_at=revision.created_at, source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY, references=references)
        return self.archive.append(submission, canonical(revision.model_dump(mode="json")).encode())

    def append_artifact_link(self, link: ArtifactLink) -> StoredVersion:
        if not isinstance(link, ArtifactLink):
            raise TypeError("append_artifact_link requires an ArtifactLink")
        link = ArtifactLink.model_validate_json(link.model_dump_json(warnings=False))
        revision = self.load_revision(link.revision_id)
        if revision.theme_id != link.theme_id:
            raise ResearchError("Artifact link crosses research themes")
        artifact = self.archive.get(link.artifact_version_id)
        if artifact.submission.spec_sha256 != revision.spec_sha256:
            raise ResearchError("Artifact uses a different specification")
        references = (
            VersionReference(target_version_id=link.revision_id,
                             use=ReferenceUse.BASIS, locator="exact research revision"),
            VersionReference(target_version_id=link.artifact_version_id,
                             use=ReferenceUse.SUPPORT, locator=link.role.value.lower()),
        )
        submission = VersionSubmission(
            schema_version=2, object_id=self._link_object(link.theme_id, link.link_id),
            kind=ObjectKind.ARTIFACT_LINK, version_id=link.link_id, title=f"{link.theme_id} {link.role.value}",
            spec_sha256=revision.spec_sha256, created_at=link.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY, references=references)
        return self.archive.append(submission, canonical(link.model_dump(mode="json")).encode())

    def load_revision(self, revision_id: str) -> ResearchRevision:
        stored = self.archive.get(revision_id)
        if stored.submission.kind is not ObjectKind.RESEARCH_REVISION:
            raise ResearchError("Requested version is not a research revision")
        return ResearchRevision.model_validate_json(self.archive.read_body(revision_id))

    def current_revision(self, theme_id: str) -> ResearchRevision | None:
        stored = self.archive.latest(self._revision_object(theme_id))
        return None if stored is None else self.load_revision(stored.submission.version_id)

    def _load_link(self, link_id: str) -> ArtifactLink:
        stored = self.archive.get(link_id)
        if stored.submission.kind is not ObjectKind.ARTIFACT_LINK:
            raise ResearchError("Requested version is not an artifact link")
        return ArtifactLink.model_validate_json(self.archive.read_body(link_id))

    def commit(self, request: ResearchCommitRequest) -> StoredVersion:
        if not isinstance(request, ResearchCommitRequest):
            raise TypeError("commit requires a ResearchCommitRequest")
        request = ResearchCommitRequest.model_validate_json(request.model_dump_json(warnings=False))
        revision = self.load_revision(request.revision_id)
        if revision.theme_id != request.theme_id or revision.spec_sha256 != request.spec_sha256:
            raise ResearchError("Commit and revision identities differ")
        current = self.current_revision(request.theme_id)
        if current is None or current.revision_id != request.revision_id:
            raise ResearchError("Research revision is no longer current")
        latest_commit = self.archive.latest(self._commit_object(request.theme_id))
        current_commit_id = latest_commit.submission.version_id if latest_commit else None
        if current_commit_id != request.expected_commit_id:
            raise Conflict("Research commit is stale")
        artifacts = []
        for link_id in request.link_ids:
            link = self._load_link(link_id)
            if link.theme_id != request.theme_id or link.revision_id != request.revision_id:
                raise ResearchError("Output link does not share the exact research revision")
            self.archive.get(link.artifact_version_id)
            artifacts.append(ArtifactBinding(link_id=link.link_id,
                artifact_version_id=link.artifact_version_id, role=link.role))
        commit = ResearchCommit(commit_id=request.commit_id, theme_id=request.theme_id,
            spec_sha256=request.spec_sha256, revision_id=request.revision_id,
            expected_commit_id=request.expected_commit_id, artifacts=tuple(artifacts),
            created_at=request.created_at)
        references = [VersionReference(target_version_id=request.revision_id,
                                       use=ReferenceUse.BASIS, locator="research revision")]
        references.extend(VersionReference(target_version_id=item.link_id,
                                           use=ReferenceUse.SUPPORT, locator=item.role.value.lower())
                          for item in commit.artifacts)
        submission = VersionSubmission(
            schema_version=2, object_id=self._commit_object(request.theme_id),
            kind=ObjectKind.RESEARCH_COMMIT, version_id=request.commit_id,
            parent_version_id=request.expected_commit_id,
            title=f"{request.theme_id} research commit", spec_sha256=request.spec_sha256,
            created_at=request.created_at, source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY, references=tuple(references))
        return self.archive.append(submission, canonical(commit.model_dump(mode="json")).encode())

    def current_commit(self, theme_id: str) -> ResearchCommit | None:
        stored = self.archive.latest(self._commit_object(theme_id))
        if stored is None:
            return None
        if stored.submission.kind is not ObjectKind.RESEARCH_COMMIT:
            raise ResearchError("Latest theme commit has the wrong object kind")
        return ResearchCommit.model_validate_json(self.archive.read_body(stored.submission.version_id))

    def is_current(self, commit_id: str) -> bool:
        try:
            stored = self.archive.get(commit_id)
            if stored.submission.kind is not ObjectKind.RESEARCH_COMMIT:
                return False
            commit = ResearchCommit.model_validate_json(self.archive.read_body(commit_id))
            revision = self.current_revision(commit.theme_id)
            latest = self.current_commit(commit.theme_id)
            if revision is None or latest is None:
                return False
            if revision.revision_id != commit.revision_id or latest.commit_id != commit_id:
                return False
            for binding in commit.artifacts:
                link = self._load_link(binding.link_id)
                if (link.revision_id != commit.revision_id
                        or link.artifact_version_id != binding.artifact_version_id):
                    return False
                artifact = self.archive.get(binding.artifact_version_id)
                if artifact.submission.spec_sha256 != commit.spec_sha256:
                    return False
            return True
        except (ArchiveError, ValueError):
            return False
