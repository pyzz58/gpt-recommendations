"""W16 shared research revision and atomic commit boundary.

This module binds research outputs to one exact revision, records each artifact's
actual referenced basis, and permits reuse of an old artifact only through an
explicit Review-backed record for non-critical changes. It does not judge content,
adopt an artifact or authorize publication. Parent-version and expected-current
checks use the shared Archive's immediate SQLite write transaction, so a stale
holder cannot overwrite a newer revision or commit against a revision that changed
after external checks.
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
    schema_version: Literal[1, 2] = 2
    revision_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    based_on_revision_id: Identifier | None = None
    input_version_ids: tuple[Identifier, ...] = ()
    question_version_id: Identifier | None = None
    evidence_version_ids: tuple[Identifier, ...] = ()
    knowledge_cutoff_version_id: Identifier | None = None
    limitation_version_ids: tuple[Identifier, ...] = ()
    noncritical_input_version_ids: tuple[Identifier, ...] = ()
    reason: NonBlank
    created_at: AwareDatetime

    @model_validator(mode="after")
    def unique_inputs(self) -> Self:
        groups = (
            ("input", self.input_version_ids),
            ("evidence", self.evidence_version_ids),
            ("limitation", self.limitation_version_ids),
            ("noncritical input", self.noncritical_input_version_ids),
        )
        for name, values in groups:
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate research revision {name}")
        inputs = set(self.input_version_ids)
        structured = {
            value for value in (
                self.question_version_id,
                self.knowledge_cutoff_version_id,
                *self.evidence_version_ids,
                *self.limitation_version_ids,
                *self.noncritical_input_version_ids,
            ) if value is not None
        }
        if not structured <= inputs:
            raise ValueError("Structured research dependencies must be declared inputs")
        if self.revision_id == self.based_on_revision_id:
            raise ValueError("A revision cannot be based on itself")
        return self


class ArtifactLink(Contract):
    schema_version: Literal[1, 2] = 2
    link_id: Identifier
    theme_id: Identifier
    revision_id: Identifier
    artifact_version_id: Identifier
    role: ResearchRole
    basis_version_ids: tuple[Identifier, ...] = ()
    compatibility_id: Identifier | None = None
    created_at: AwareDatetime

    @model_validator(mode="after")
    def distinct_versions(self) -> Self:
        if self.link_id == self.artifact_version_id:
            raise ValueError("Artifact and link IDs must differ")
        if len(self.basis_version_ids) != len(set(self.basis_version_ids)):
            raise ValueError("Duplicate artifact basis version")
        return self


class ResearchCommitRequest(Contract):
    schema_version: Literal[1, 2] = 2
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
    basis_version_ids: tuple[Identifier, ...] = ()
    compatibility_id: Identifier | None = None


class ResearchCommit(Contract):
    schema_version: Literal[1, 2] = 2
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


class ArtifactCompatibility(Contract):
    schema_version: Literal[1] = 1
    compatibility_id: Identifier
    theme_id: Identifier
    artifact_version_id: Identifier
    source_revision_id: Identifier
    target_revision_id: Identifier
    review_version_id: Identifier
    reviewed_input_version_ids: tuple[Identifier, ...]
    accepted_added_input_version_ids: tuple[Identifier, ...] = ()
    accepted_removed_dependency_ids: tuple[Identifier, ...] = ()
    reason: NonBlank
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.source_revision_id == self.target_revision_id:
            raise ValueError("Compatibility needs two different revisions")
        groups = (
            ("reviewed input", self.reviewed_input_version_ids),
            ("accepted added input", self.accepted_added_input_version_ids),
            ("accepted removed dependency", self.accepted_removed_dependency_ids),
        )
        for name, values in groups:
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate {name}")
        if not set(self.accepted_added_input_version_ids) <= set(
                self.reviewed_input_version_ids):
            raise ValueError("Accepted additions must be reviewed target inputs")
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
            stored = self.archive.get(version_id)
            if stored.body_retention_revoked:
                raise ResearchError(f"Research input was withdrawn: {version_id}")
        for version_id in revision.evidence_version_ids:
            stored = self.archive.get(version_id)
            if stored.submission.kind is not ObjectKind.EVIDENCE:
                raise ResearchError("Declared research evidence is not an Evidence version")
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

    def _artifact_provenance(
            self, artifact_version_id: str) -> tuple[StoredVersion, tuple[str, ...],
                                                     tuple[str, ...]]:
        artifact = self.archive.get(artifact_version_id)
        basis = set()
        source_revisions = set()
        for reference in artifact.submission.references:
            target = self.archive.get(reference.target_version_id)
            if target.submission.kind is ObjectKind.RESEARCH_REVISION:
                source_revisions.add(reference.target_version_id)
            elif target.submission.kind not in (
                    ObjectKind.ARTIFACT_LINK, ObjectKind.ARTIFACT_COMPATIBILITY):
                basis.add(reference.target_version_id)
        return artifact, tuple(sorted(basis)), tuple(sorted(source_revisions))

    def load_compatibility(self, compatibility_id: str) -> ArtifactCompatibility:
        stored = self.archive.get(compatibility_id)
        if stored.submission.kind is not ObjectKind.ARTIFACT_COMPATIBILITY:
            raise ResearchError("Requested version is not an artifact compatibility record")
        return ArtifactCompatibility.model_validate_json(
            self.archive.read_body(compatibility_id))

    def append_compatibility(
            self, compatibility: ArtifactCompatibility) -> StoredVersion:
        if not isinstance(compatibility, ArtifactCompatibility):
            raise TypeError("append_compatibility requires ArtifactCompatibility")
        compatibility = ArtifactCompatibility.model_validate_json(
            compatibility.model_dump_json(warnings=False))
        source = self.load_revision(compatibility.source_revision_id)
        target = self.load_revision(compatibility.target_revision_id)
        if (source.theme_id != compatibility.theme_id
                or target.theme_id != compatibility.theme_id
                or source.spec_sha256 != target.spec_sha256):
            raise ResearchError("Compatibility revisions cross theme or specification")
        current = self.current_revision(compatibility.theme_id)
        if current is None or current.revision_id != target.revision_id:
            raise ResearchError("Compatibility target revision is not current")
        artifact, basis, source_revisions = self._artifact_provenance(
            compatibility.artifact_version_id)
        if artifact.body_retention_revoked:
            raise ResearchError("Compatibility artifact was withdrawn")
        if artifact.submission.spec_sha256 != target.spec_sha256:
            raise ResearchError("Compatibility artifact uses a different specification")
        if compatibility.source_revision_id not in source_revisions:
            raise ResearchError("Compatibility source is not an artifact revision dependency")
        if set(compatibility.reviewed_input_version_ids) != set(target.input_version_ids):
            raise ResearchError("Compatibility did not review the exact target inputs")
        added = set(target.input_version_ids) - set(source.input_version_ids)
        removed = set(source.input_version_ids) - set(target.input_version_ids)
        if set(compatibility.accepted_added_input_version_ids) != added:
            raise ResearchError("Compatibility must explicitly account for every added input")
        if set(compatibility.accepted_removed_dependency_ids) != removed:
            raise ResearchError("Compatibility must explicitly account for every removed dependency")
        noncritical_target = set(target.noncritical_input_version_ids)
        noncritical_source = set(source.noncritical_input_version_ids)
        if added - noncritical_target:
            raise ResearchError("A critical added input requires a rebuilt artifact")
        if removed - noncritical_source:
            raise ResearchError("A critical removed dependency requires a rebuilt artifact")
        review = self.archive.get(compatibility.review_version_id)
        if review.submission.kind is not ObjectKind.REVIEW:
            raise ResearchError("Compatibility needs an archived Review")
        if review.submission.spec_sha256 != target.spec_sha256:
            raise ResearchError("Compatibility Review uses a different specification")
        if review.body_retention_revoked:
            raise ResearchError("Compatibility Review was withdrawn")
        reviewed_targets = {
            item.target_version_id for item in review.submission.references
            if item.use is ReferenceUse.REVIEW_OF
        }
        required_targets = {
            compatibility.artifact_version_id,
            compatibility.source_revision_id,
            compatibility.target_revision_id,
        }
        if not required_targets <= reviewed_targets:
            raise ResearchError("Compatibility Review does not cover exact artifact and revisions")
        references = [
            VersionReference(target_version_id=compatibility.artifact_version_id,
                             use=ReferenceUse.REVIEW_OF, locator="exact artifact"),
            VersionReference(target_version_id=compatibility.source_revision_id,
                             use=ReferenceUse.BASIS, locator="source revision"),
            VersionReference(target_version_id=compatibility.target_revision_id,
                             use=ReferenceUse.BASIS, locator="target revision"),
            VersionReference(target_version_id=compatibility.review_version_id,
                             use=ReferenceUse.SUPPORT, locator="compatibility review"),
        ]
        references.extend(
            VersionReference(target_version_id=version_id,
                             use=ReferenceUse.SUPPORT, locator=f"reviewed input {index}")
            for index, version_id in enumerate(
                compatibility.reviewed_input_version_ids))
        submission = VersionSubmission(
            schema_version=2, object_id=f"COMPAT-{compatibility.compatibility_id}",
            kind=ObjectKind.ARTIFACT_COMPATIBILITY,
            version_id=compatibility.compatibility_id,
            title=f"{compatibility.theme_id} artifact compatibility",
            spec_sha256=target.spec_sha256, created_at=compatibility.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY, references=tuple(references))
        return self.archive.append(
            submission, canonical(compatibility.model_dump(mode="json")).encode())

    def append_artifact_link(self, link: ArtifactLink) -> StoredVersion:
        if not isinstance(link, ArtifactLink):
            raise TypeError("append_artifact_link requires an ArtifactLink")
        link = ArtifactLink.model_validate_json(link.model_dump_json(warnings=False))
        revision = self.load_revision(link.revision_id)
        if revision.theme_id != link.theme_id:
            raise ResearchError("Artifact link crosses research themes")
        artifact, actual_basis, source_revisions = self._artifact_provenance(
            link.artifact_version_id)
        if artifact.body_retention_revoked:
            raise ResearchError("Artifact was withdrawn")
        if artifact.submission.spec_sha256 != revision.spec_sha256:
            raise ResearchError("Artifact uses a different specification")
        if link.schema_version >= 2 and set(link.basis_version_ids) != set(actual_basis):
            raise ResearchError("Artifact link basis does not match actual artifact references")
        if link.compatibility_id is not None:
            compatibility = self.load_compatibility(link.compatibility_id)
            if (compatibility.theme_id != link.theme_id
                    or compatibility.artifact_version_id != link.artifact_version_id
                    or compatibility.target_revision_id != link.revision_id
                    or compatibility.source_revision_id not in source_revisions):
                raise ResearchError("Artifact link and compatibility identities differ")
        references = [
            VersionReference(target_version_id=link.revision_id,
                             use=ReferenceUse.BASIS, locator="exact research revision"),
            VersionReference(target_version_id=link.artifact_version_id,
                             use=ReferenceUse.SUPPORT, locator=link.role.value.lower()),
        ]
        if link.compatibility_id is not None:
            references.append(VersionReference(
                target_version_id=link.compatibility_id,
                use=ReferenceUse.SUPPORT, locator="explicit compatibility"))
        submission = VersionSubmission(
            schema_version=2, object_id=self._link_object(link.theme_id, link.link_id),
            kind=ObjectKind.ARTIFACT_LINK, version_id=link.link_id, title=f"{link.theme_id} {link.role.value}",
            spec_sha256=revision.spec_sha256, created_at=link.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY, references=tuple(references))
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

    def _validate_artifact_link(
            self, link: ArtifactLink, revision: ResearchRevision) -> None:
        if link.schema_version < 2:
            raise ResearchError("A legacy artifact link cannot form a new research commit")
        if link.theme_id != revision.theme_id or link.revision_id != revision.revision_id:
            raise ResearchError("Output link does not share the exact research revision")
        artifact, actual_basis, source_revisions = self._artifact_provenance(
            link.artifact_version_id)
        if artifact.body_retention_revoked:
            raise ResearchError("Artifact was withdrawn")
        if artifact.submission.spec_sha256 != revision.spec_sha256:
            raise ResearchError("Artifact uses a different specification")
        if link.schema_version >= 2 and set(link.basis_version_ids) != set(actual_basis):
            raise ResearchError("Artifact link basis no longer matches actual references")
        basis = set(actual_basis)
        target_inputs = set(revision.input_version_ids)
        if revision.revision_id in source_revisions:
            if link.compatibility_id is not None:
                raise ResearchError("A rebuilt artifact must not carry an old compatibility record")
            if target_inputs - basis:
                raise ResearchError("Artifact omits a declared input of its own revision")
            return
        if link.compatibility_id is None:
            raise ResearchError("Relabelled artifact needs explicit compatibility review")
        compatibility = self.load_compatibility(link.compatibility_id)
        if (compatibility.theme_id != revision.theme_id
                or compatibility.artifact_version_id != link.artifact_version_id
                or compatibility.target_revision_id != revision.revision_id):
            raise ResearchError("Artifact link and compatibility identities differ")
        if compatibility.source_revision_id not in source_revisions:
            raise ResearchError("Compatibility source is not an artifact revision dependency")
        source = self.load_revision(compatibility.source_revision_id)
        if (source.theme_id != revision.theme_id
                or source.spec_sha256 != revision.spec_sha256):
            raise ResearchError("Compatibility source revision crosses theme or specification")
        if set(compatibility.reviewed_input_version_ids) != target_inputs:
            raise ResearchError("Compatibility did not review the exact target inputs")
        added = target_inputs - set(source.input_version_ids)
        removed = set(source.input_version_ids) - target_inputs
        if set(compatibility.accepted_added_input_version_ids) != added:
            raise ResearchError("Compatibility must account for every added input")
        if set(compatibility.accepted_removed_dependency_ids) != removed:
            raise ResearchError("Compatibility must account for every removed dependency")
        if added - set(revision.noncritical_input_version_ids):
            raise ResearchError("A critical added input requires a rebuilt artifact")
        if removed - set(source.noncritical_input_version_ids):
            raise ResearchError("A critical removed dependency requires a rebuilt artifact")
        common = target_inputs & set(source.input_version_ids)
        if common - basis:
            raise ResearchError("Compatibility cannot replace a common critical artifact input")
        review = self.archive.get(compatibility.review_version_id)
        if review.submission.kind is not ObjectKind.REVIEW:
            raise ResearchError("Compatibility needs an archived Review")
        if review.submission.spec_sha256 != revision.spec_sha256:
            raise ResearchError("Compatibility Review uses a different specification")
        if review.body_retention_revoked:
            raise ResearchError("Compatibility Review was withdrawn")
        reviewed_targets = {
            item.target_version_id for item in review.submission.references
            if item.use is ReferenceUse.REVIEW_OF
        }
        required_targets = {
            compatibility.artifact_version_id,
            compatibility.source_revision_id,
            compatibility.target_revision_id,
        }
        if not required_targets <= reviewed_targets:
            raise ResearchError("Compatibility Review does not cover exact artifact and revisions")

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
            self._validate_artifact_link(link, revision)
            artifacts.append(ArtifactBinding(
                link_id=link.link_id,
                artifact_version_id=link.artifact_version_id,
                role=link.role,
                basis_version_ids=link.basis_version_ids,
                compatibility_id=link.compatibility_id))
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
        return self.archive.append(
            submission, canonical(commit.model_dump(mode="json")).encode(),
            expected_current={
                self._revision_object(request.theme_id): request.revision_id,
                self._commit_object(request.theme_id): request.expected_commit_id,
            })

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
                        or link.artifact_version_id != binding.artifact_version_id
                        or link.basis_version_ids != binding.basis_version_ids
                        or link.compatibility_id != binding.compatibility_id):
                    return False
                self._validate_artifact_link(link, revision)
            return True
        except (ArchiveError, ValueError):
            return False
