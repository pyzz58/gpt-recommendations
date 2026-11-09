"""W37 short-form article routing over W23, W26 and W34 records.

The route binds a real Article to its current editorial decision, optional
source-selection material, and the exact prior-article/dossier or correction
case required by its short form. It does not judge content, create a Review or
authorize publication.
"""
from __future__ import annotations

from enum import Enum
import hashlib
from typing import Literal, Self

from pydantic import AwareDatetime, model_validator

from .archive import Archive, ArchiveError, Conflict, MissingVersion, canonical
from .contracts import (Contract, Digest, Identifier, NonBlank, ObjectKind,
                        ReferenceUse, Representation, RightsGrant,
                        SourceTimes, StoredVersion, VersionReference,
                        VersionSubmission)
from .correction import CorrectionController
from .editorial import (ArticleType, EditorialController,
                        TopicDecisionCode)
from .evidence import EvidenceController
from .materials import ChineseMaterialController
from .research import ResearchRevisionController
from .workflow import ResearchWorkflowController


class ShortFormKind(str, Enum):
    SOURCE_SELECTION = "SOURCE_SELECTION"
    INITIAL_FACT = "INITIAL_FACT"
    FOLLOW_UP = "FOLLOW_UP"
    CORRECTION = "CORRECTION"


class PriorResearchState(str, Enum):
    PUBLISHED_ARTICLE = "PUBLISHED_ARTICLE"
    UNPUBLISHED_RESEARCH = "UNPUBLISHED_RESEARCH"


class RouteResponsibility(str, Enum):
    SOURCE_VALUE_AND_LIMITS = "SOURCE_VALUE_AND_LIMITS"
    NECESSARY_BACKGROUND = "NECESSARY_BACKGROUND"
    ORIGINAL_LOCATION = "ORIGINAL_LOCATION"
    FACT_TIME_AND_EVIDENCE = "FACT_TIME_AND_EVIDENCE"
    IMPORTANCE_AND_UNKNOWNS = "IMPORTANCE_AND_UNKNOWNS"
    REOPEN_CONDITION = "REOPEN_CONDITION"
    PRIOR_REFERENCE = "PRIOR_REFERENCE"
    NEW_EVIDENCE_AND_IMPACT = "NEW_EVIDENCE_AND_IMPACT"
    ORIGINAL_CLAIM_LOCATION = "ORIGINAL_CLAIM_LOCATION"
    CORRECTION_CASE = "CORRECTION_CASE"
    INDEPENDENT_REVIEW_REQUIRED = "INDEPENDENT_REVIEW_REQUIRED"
    WEEKLY_DEPTH_REMAINS = "WEEKLY_DEPTH_REMAINS"


class ArticleRouteRequest(Contract):
    schema_version: Literal[1] = 1
    route_id: Identifier
    spec_sha256: Digest
    task_version_id: Identifier
    topic_decision_id: Identifier
    research_admission_id: Identifier
    article_version_id: Identifier
    short_form: ShortFormKind
    material_version_id: Identifier | None = None
    evidence_version_ids: tuple[Identifier, ...]
    prior_article_version_id: Identifier | None = None
    prior_dossier_version_id: Identifier | None = None
    prior_state: PriorResearchState | None = None
    correction_case_version_id: Identifier | None = None
    source_value: NonBlank | None = None
    background: NonBlank | None = None
    limitations: tuple[NonBlank, ...] = ()
    fact_time: AwareDatetime | None = None
    what_happened: NonBlank | None = None
    why_important: NonBlank | None = None
    unknowns: tuple[NonBlank, ...] = ()
    reopen_conditions: tuple[NonBlank, ...] = ()
    change_summary: NonBlank | None = None
    impact_summary: NonBlank | None = None
    previous_excerpt_locator: NonBlank | None = None
    previous_excerpt: NonBlank | None = None
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for name, values in (
                ("evidence", self.evidence_version_ids),
                ("limitation", self.limitations),
                ("unknown", self.unknowns),
                ("reopen condition", self.reopen_conditions)):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate article-route {name}")
        if not self.evidence_version_ids:
            raise ValueError("Article route needs exact Evidence")

        def require(name: str, value) -> None:
            if value in (None, "", ()):
                raise ValueError(
                    f"{self.short_form.value} route needs {name}")

        def forbid(names: tuple[str, ...]) -> None:
            present = [
                name for name in names
                if getattr(self, name) not in (None, (), "")]
            if present:
                raise ValueError(
                    f"{self.short_form.value} route cannot carry {','.join(present)}")

        if self.short_form is ShortFormKind.SOURCE_SELECTION:
            require("material_version_id", self.material_version_id)
            require("source_value", self.source_value)
            require("background", self.background)
            require("limitations", self.limitations)
            forbid((
                "prior_article_version_id", "prior_dossier_version_id",
                "prior_state", "correction_case_version_id",
                "previous_excerpt_locator", "previous_excerpt"))
        elif self.short_form is ShortFormKind.INITIAL_FACT:
            require("fact_time", self.fact_time)
            require("what_happened", self.what_happened)
            require("why_important", self.why_important)
            require("unknowns", self.unknowns)
            require("reopen_conditions", self.reopen_conditions)
            forbid((
                "prior_article_version_id", "prior_dossier_version_id",
                "prior_state", "correction_case_version_id",
                "previous_excerpt_locator", "previous_excerpt"))
        elif self.short_form is ShortFormKind.FOLLOW_UP:
            require("what_happened", self.what_happened)
            require("why_important", self.why_important)
            require("unknowns", self.unknowns)
            require("reopen_conditions", self.reopen_conditions)
            require("change_summary", self.change_summary)
            require("impact_summary", self.impact_summary)
            require("prior_state", self.prior_state)
            if ((self.prior_article_version_id is None)
                    == (self.prior_dossier_version_id is None)):
                raise ValueError(
                    "FOLLOW_UP needs exactly one prior Article or Dossier")
            if self.prior_article_version_id is not None:
                if self.prior_state is not PriorResearchState.PUBLISHED_ARTICLE:
                    raise ValueError(
                        "Prior Article FOLLOW_UP needs PUBLISHED_ARTICLE state")
            elif self.prior_state is not PriorResearchState.UNPUBLISHED_RESEARCH:
                raise ValueError(
                    "Prior Dossier FOLLOW_UP needs UNPUBLISHED_RESEARCH state")
            if self.correction_case_version_id is not None:
                raise ValueError("FOLLOW_UP cannot substitute for CORRECTION")
        else:
            require("prior_article_version_id",
                    self.prior_article_version_id)
            require("correction_case_version_id",
                    self.correction_case_version_id)
            require("what_happened", self.what_happened)
            require("why_important", self.why_important)
            require("impact_summary", self.impact_summary)
            require("previous_excerpt_locator",
                    self.previous_excerpt_locator)
            require("previous_excerpt", self.previous_excerpt)
            if self.prior_state is not PriorResearchState.PUBLISHED_ARTICLE:
                raise ValueError(
                    "CORRECTION needs a prior PUBLISHED_ARTICLE")
            if self.prior_dossier_version_id is not None:
                raise ValueError("CORRECTION cannot point only to a Dossier")
        return self


class ArticleRouteRecord(Contract):
    schema_version: Literal[1] = 1
    route_id: Identifier
    route_version_id: Identifier
    spec_sha256: Digest
    task_version_id: Identifier
    topic_decision_id: Identifier
    research_admission_id: Identifier
    topic_id: Identifier
    theme_id: Identifier
    edition_id: Identifier
    article_type: ArticleType
    article_version_id: Identifier
    short_form: ShortFormKind
    material_version_id: Identifier | None
    evidence_version_ids: tuple[Identifier, ...]
    prior_article_version_id: Identifier | None
    prior_dossier_version_id: Identifier | None
    prior_state: PriorResearchState | None
    correction_case_version_id: Identifier | None
    source_value: NonBlank | None
    background: NonBlank | None
    limitations: tuple[NonBlank, ...]
    fact_time: AwareDatetime | None
    what_happened: NonBlank | None
    why_important: NonBlank | None
    unknowns: tuple[NonBlank, ...]
    reopen_conditions: tuple[NonBlank, ...]
    change_summary: NonBlank | None
    impact_summary: NonBlank | None
    previous_excerpt_locator: NonBlank | None
    previous_excerpt: NonBlank | None
    required_responsibilities: tuple[RouteResponsibility, ...]
    content_review_required: Literal[True] = True
    publication_authorized: Literal[False] = False
    created_at: AwareDatetime


class ArticleRouteError(ArchiveError):
    """Route identity/completeness failure, never a content decision."""


def _digest(value) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _version(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([prefix, identity]).encode()).hexdigest()[:32]


def _object(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([identity]).encode()).hexdigest()[:32]


def _responsibilities(kind: ShortFormKind) -> tuple[RouteResponsibility, ...]:
    common = (
        RouteResponsibility.INDEPENDENT_REVIEW_REQUIRED,
        RouteResponsibility.WEEKLY_DEPTH_REMAINS,
    )
    if kind is ShortFormKind.SOURCE_SELECTION:
        return (
            RouteResponsibility.SOURCE_VALUE_AND_LIMITS,
            RouteResponsibility.NECESSARY_BACKGROUND,
            RouteResponsibility.ORIGINAL_LOCATION,
            *common,
        )
    if kind is ShortFormKind.INITIAL_FACT:
        return (
            RouteResponsibility.FACT_TIME_AND_EVIDENCE,
            RouteResponsibility.IMPORTANCE_AND_UNKNOWNS,
            RouteResponsibility.REOPEN_CONDITION,
            *common,
        )
    if kind is ShortFormKind.FOLLOW_UP:
        return (
            RouteResponsibility.PRIOR_REFERENCE,
            RouteResponsibility.FACT_TIME_AND_EVIDENCE,
            RouteResponsibility.NEW_EVIDENCE_AND_IMPACT,
            RouteResponsibility.REOPEN_CONDITION,
            *common,
        )
    return (
        RouteResponsibility.PRIOR_REFERENCE,
        RouteResponsibility.ORIGINAL_CLAIM_LOCATION,
        RouteResponsibility.CORRECTION_CASE,
        RouteResponsibility.NEW_EVIDENCE_AND_IMPACT,
        *common,
    )


class ArticleRouteController:
    def __init__(self, archive: Archive, rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError("ArticleRouteController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError(
                "ArticleRouteController requires an internal journal grant")
        self.archive = archive
        self.rights = rights
        self.editorial = EditorialController(archive, rights)
        self.evidence = EvidenceController(archive, rights)
        self.materials = ChineseMaterialController(archive, rights)
        self.corrections = CorrectionController(archive, rights)
        self.workflow = ResearchWorkflowController(archive, rights)
        self.research = ResearchRevisionController(archive, rights)

    @staticmethod
    def _current(stored: StoredVersion, label: str,
                 archive: Archive) -> None:
        latest = archive.latest(stored.submission.object_id)
        if latest is None or latest.submission.version_id != (
                stored.submission.version_id):
            raise ArticleRouteError(f"{label} is not current")

    def _decision_and_admission(
            self, request: ArticleRouteRequest
    ) -> tuple:
        decision = self.editorial.load_decision(
            request.topic_decision_id)
        current = self.editorial.current_decision(decision.topic_id)
        if current is None or current.decision_id != decision.decision_id:
            raise ArticleRouteError("Article route uses a stale TopicDecision")
        if decision.decision is not TopicDecisionCode.COVER:
            raise ArticleRouteError("Short-form route needs an S8 COVER decision")
        expected_type = (
            ArticleType.SOURCE_SELECTION
            if request.short_form is ShortFormKind.SOURCE_SELECTION
            else ArticleType.UPDATE_CORRECTION)
        if decision.article_type is not expected_type:
            raise ArticleRouteError(
                "Short form and W23 article type differ")
        admission = self.editorial.load_research_admission(
            request.research_admission_id)
        admission_stored = self.archive.get(
            EditorialController._version(
                "RESEARCH-ADMISSION-",
                admission.research_admission_id))
        self._current(admission_stored, "research admission", self.archive)
        if (admission.topic_decision_id != decision.decision_id
                or admission.spec_sha256 != request.spec_sha256
                or set(admission.allowed_article_types) != {
                    expected_type}):
            raise ArticleRouteError(
                "Research admission does not match this short-form route")
        self.editorial._current_decision_context(decision.decision_id)
        decision_stored = self.archive.get(
            EditorialController._version(
                "TOPIC-DECISION-", decision.decision_id))
        return decision, decision_stored, admission, admission_stored

    def record(self, request: ArticleRouteRequest) -> StoredVersion:
        if not isinstance(request, ArticleRouteRequest):
            raise TypeError("record requires ArticleRouteRequest")
        request = ArticleRouteRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        decision, decision_stored, admission, admission_stored = (
            self._decision_and_admission(request))
        task = self.archive.get(request.task_version_id)
        if (task.submission.kind is not ObjectKind.TASK
                or task.submission.spec_sha256 != request.spec_sha256):
            raise ArticleRouteError("Article route task is invalid")
        self._current(task, "task", self.archive)
        article = self.archive.get(request.article_version_id)
        if (article.submission.kind is not ObjectKind.ARTICLE
                or article.submission.spec_sha256 != request.spec_sha256
                or article.submission.representation is not (
                    Representation.FULL_BODY)
                or article.body_retention_revoked
                or not self.archive.read_body(
                    request.article_version_id)):
            raise ArticleRouteError(
                "Article route needs a current retained reader Article")
        self._current(article, "Article route reader draft", self.archive)
        try:
            article_text = self.archive.read_body(
                request.article_version_id).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ArticleRouteError(
                "Article route reader draft is not UTF-8") from exc

        evidence_stored = []
        for evidence_id in request.evidence_version_ids:
            stored = self.archive.get(evidence_id)
            evidence = self.evidence.load_evidence(evidence_id)
            if (stored.submission.kind is not ObjectKind.EVIDENCE
                    or evidence.theme_id != decision.theme_id
                    or evidence.spec_sha256 != request.spec_sha256):
                raise ArticleRouteError(
                    "Article route Evidence crosses theme or specification")
            self._current(stored, "Article route Evidence", self.archive)
            evidence_stored.append(stored)

        material = None
        material_stored = None
        if request.material_version_id is not None:
            material_stored = self.archive.get(request.material_version_id)
            material = self.materials.load_material(
                request.material_version_id)
            if (material_stored.submission.kind is not (
                    ObjectKind.CHINESE_MATERIAL)
                    or material.topic_decision_id != decision.decision_id
                    or material.spec_sha256 != request.spec_sha256
                    or not set(material.evidence_version_ids) <= set(
                        request.evidence_version_ids)):
                raise ArticleRouteError(
                    "Short-form Chinese material crosses its route basis")
            self._current(
                material_stored, "Chinese source-selection material",
                self.archive)

        prior_article = None
        if request.prior_article_version_id is not None:
            prior_article = self.archive.get(
                request.prior_article_version_id)
            if (prior_article.submission.kind is not ObjectKind.ARTICLE
                    or prior_article.submission.spec_sha256
                    != request.spec_sha256
                    or prior_article.body_retention_revoked):
                raise ArticleRouteError(
                    "Prior publication is not an available Article")
        prior_dossier = None
        if request.prior_dossier_version_id is not None:
            prior_dossier = self.workflow.load_snapshot(
                request.prior_dossier_version_id)
            if prior_dossier.spec_sha256 != request.spec_sha256:
                raise ArticleRouteError(
                    "Prior research Dossier uses another specification")
            revision = self.research.load_revision(
                prior_dossier.revision_id)
            if revision.theme_id != prior_dossier.theme_id:
                raise ArticleRouteError(
                    "Prior research Dossier and revision differ")
            previous_inputs = set(revision.input_version_ids)
        elif prior_article is not None:
            previous_inputs = {
                item.target_version_id
                for item in prior_article.submission.references}
        else:
            previous_inputs = set()
        if request.short_form in (
                ShortFormKind.FOLLOW_UP, ShortFormKind.CORRECTION):
            if not (set(request.evidence_version_ids) - previous_inputs):
                raise ArticleRouteError(
                    "Follow-up/correction needs evidence beyond the prior basis")

        correction_case = None
        correction_stored = None
        if request.correction_case_version_id is not None:
            correction_stored = self.archive.get(
                request.correction_case_version_id)
            correction_case = self.corrections.load(
                request.correction_case_version_id)
            self._current(
                correction_stored, "correction case", self.archive)
            old_text = (
                self.archive.read_body(
                    request.prior_article_version_id).decode("utf-8")
                if request.prior_article_version_id is not None else "")
            if (correction_case.spec_sha256 != request.spec_sha256
                    or request.prior_article_version_id not in (
                        *correction_case.affected_version_ids,
                        correction_case.change.previous_version_id)
                    or request.previous_excerpt not in article_text
                    or request.previous_excerpt not in old_text):
                raise ArticleRouteError(
                    "Correction route does not bind the affected old Article "
                    "and exact excerpt: "
                    f"affected={correction_case.affected_version_ids!r}, "
                    f"new_contains={request.previous_excerpt in article_text}, "
                    f"old_contains={request.previous_excerpt in old_text}")

        required_refs = {
            decision_stored.submission.version_id,
            admission_stored.submission.version_id,
            request.task_version_id,
            *request.evidence_version_ids,
        }
        if material_stored is not None:
            required_refs.add(material_stored.submission.version_id)
        if prior_article is not None:
            required_refs.add(prior_article.submission.version_id)
        if prior_dossier is not None:
            required_refs.add(request.prior_dossier_version_id)
        if correction_stored is not None:
            required_refs.add(correction_stored.submission.version_id)
        if not required_refs <= {
                item.target_version_id
                for item in article.submission.references}:
            raise ArticleRouteError(
                "Reader Article references do not bind every route dependency")

        dependency_times = [
            decision.created_at, admission.created_at,
            article.submission.created_at,
            *(item.submission.created_at for item in evidence_stored),
        ]
        if material is not None:
            dependency_times.append(material.created_at)
        if correction_case is not None:
            dependency_times.append(correction_case.updated_at)
        if request.created_at < max(dependency_times):
            raise ArticleRouteError(
                "Article route predates one of its exact dependencies")

        version_id = _version(
            "ARTICLE-ROUTE-",
            canonical([request.route_id, _digest(
                request.model_dump(mode="json"))]))
        object_id = _object("ARTICLE-ROUTE-OBJECT-", request.route_id)
        record = ArticleRouteRecord(
            route_id=request.route_id, route_version_id=version_id,
            spec_sha256=request.spec_sha256,
            task_version_id=request.task_version_id,
            topic_decision_id=decision.decision_id,
            research_admission_id=admission.research_admission_id,
            topic_id=decision.topic_id, theme_id=decision.theme_id,
            edition_id=decision.edition_id,
            article_type=decision.article_type,
            article_version_id=request.article_version_id,
            short_form=request.short_form,
            material_version_id=request.material_version_id,
            evidence_version_ids=request.evidence_version_ids,
            prior_article_version_id=(
                request.prior_article_version_id),
            prior_dossier_version_id=(
                request.prior_dossier_version_id),
            prior_state=request.prior_state,
            correction_case_version_id=(
                request.correction_case_version_id),
            source_value=request.source_value,
            background=request.background,
            limitations=request.limitations,
            fact_time=request.fact_time,
            what_happened=request.what_happened,
            why_important=request.why_important,
            unknowns=request.unknowns,
            reopen_conditions=request.reopen_conditions,
            change_summary=request.change_summary,
            impact_summary=request.impact_summary,
            previous_excerpt_locator=(
                request.previous_excerpt_locator),
            previous_excerpt=request.previous_excerpt,
            required_responsibilities=_responsibilities(
                request.short_form),
            created_at=request.created_at)
        refs = [
            VersionReference(
                target_version_id=decision_stored.submission.version_id,
                use=ReferenceUse.BASIS, locator="W23 S8 COVER"),
            VersionReference(
                target_version_id=admission_stored.submission.version_id,
                use=ReferenceUse.BASIS, locator="research admission"),
            VersionReference(
                target_version_id=request.task_version_id,
                use=ReferenceUse.BASIS, locator="route task"),
            VersionReference(
                target_version_id=request.article_version_id,
                use=ReferenceUse.REVIEW_OF, locator="routed reader Article"),
            *(
                VersionReference(
                    target_version_id=version,
                    use=ReferenceUse.SUPPORT,
                    locator="routed exact dependency")
                for version in sorted(required_refs - {
                    decision_stored.submission.version_id,
                    admission_stored.submission.version_id,
                    request.task_version_id,
                    request.article_version_id})
            ),
        ]
        submission = VersionSubmission(
            schema_version=2, object_id=object_id, version_id=version_id,
            kind=ObjectKind.ARTICLE_ROUTE,
            title=f"article route {request.route_id}",
            spec_sha256=request.spec_sha256,
            created_at=request.created_at, source_times=SourceTimes(),
            rights=self.rights, representation=Representation.FULL_BODY,
            references=tuple(refs))
        latest = self.archive.latest(object_id)
        if latest is not None:
            try:
                existing = self.load(latest.submission.version_id)
            except ArticleRouteError:
                existing = None
            if existing is not None and existing.route_version_id == version_id:
                return latest
            if existing is None or existing.route_version_id != version_id:
                raise Conflict(
                    "Article route ID already has different current content")
        try:
            return self.archive.append(
                submission,
                canonical(record.model_dump(mode="json")).encode(),
                expected_current={object_id: None} if latest is None else None)
        except Conflict:
            current = self.archive.latest(object_id)
            if current is not None and current.submission.version_id == version_id:
                return current
            raise

    def load(self, route_version_id: str) -> ArticleRouteRecord:
        stored = self.archive.get(route_version_id)
        if stored.submission.kind is not ObjectKind.ARTICLE_ROUTE:
            raise ArticleRouteError("Requested version is not an ArticleRoute")
        record = ArticleRouteRecord.model_validate_json(
            self.archive.read_body(route_version_id))
        if (record.route_version_id != route_version_id
                or stored.submission.spec_sha256 != record.spec_sha256
                or stored.submission.created_at != record.created_at):
            raise ArticleRouteError("Article route identity mismatch")
        return record

    def require_current(
            self, route_version_id: str,
            current_article_version_id: str) -> ArticleRouteRecord:
        record = self.load(route_version_id)
        stored = self.archive.get(route_version_id)
        self._current(stored, "Article route", self.archive)
        decision = self.editorial.load_decision(record.topic_decision_id)
        current_decision = self.editorial.current_decision(record.topic_id)
        if (current_decision is None
                or current_decision.decision_id != decision.decision_id
                or decision.theme_id != record.theme_id
                or decision.edition_id != record.edition_id
                or decision.article_type is not record.article_type):
            raise ArticleRouteError("Article route editorial basis is stale")
        self.editorial._current_decision_context(decision.decision_id)
        admission = self.editorial.load_research_admission(
            record.research_admission_id)
        admission_stored = self.archive.get(
            EditorialController._version(
                "RESEARCH-ADMISSION-",
                record.research_admission_id))
        self._current(admission_stored, "research admission", self.archive)
        if (admission.topic_decision_id != decision.decision_id
                or set(admission.allowed_article_types) != {
                    record.article_type}):
            raise ArticleRouteError("Article route research admission is stale")
        task = self.archive.get(record.task_version_id)
        self._current(task, "route task", self.archive)
        for evidence_id in record.evidence_version_ids:
            evidence = self.evidence.load_evidence(evidence_id)
            evidence_stored = self.archive.get(evidence_id)
            if (evidence.theme_id != record.theme_id
                    or evidence.spec_sha256 != record.spec_sha256):
                raise ArticleRouteError("Article route Evidence is stale")
            self._current(evidence_stored, "Article route Evidence", self.archive)
        if record.material_version_id is not None:
            material = self.materials.load_material(
                record.material_version_id)
            material_stored = self.archive.get(record.material_version_id)
            if (material.topic_decision_id != record.topic_decision_id
                    or material.spec_sha256 != record.spec_sha256):
                raise ArticleRouteError("Source-selection material is stale")
            self._current(
                material_stored, "source-selection material", self.archive)
        if record.correction_case_version_id is not None:
            correction_stored = self.archive.get(
                record.correction_case_version_id)
            self.corrections.load(record.correction_case_version_id)
            self._current(
                correction_stored, "correction case", self.archive)
        article = self.archive.get(current_article_version_id)
        if (article.submission.kind is not ObjectKind.ARTICLE
                or article.submission.spec_sha256 != record.spec_sha256
                or article.submission.representation is not (
                    Representation.FULL_BODY)
                or article.body_retention_revoked):
            raise ArticleRouteError("Routed reviewer Article is unavailable")
        self._current(article, "routed reviewer Article", self.archive)
        history = self.archive.history(article.submission.object_id)
        if record.article_version_id not in {
                item.submission.version_id for item in history}:
            raise ArticleRouteError(
                "Current Article is not a version of the routed draft")
        required_refs = {
            self.archive.get(EditorialController._version(
                "TOPIC-DECISION-", record.topic_decision_id)
            ).submission.version_id,
            self.archive.get(EditorialController._version(
                "RESEARCH-ADMISSION-",
                record.research_admission_id)).submission.version_id,
            record.task_version_id,
            *record.evidence_version_ids,
        }
        if record.material_version_id is not None:
            required_refs.add(record.material_version_id)
        if record.prior_article_version_id is not None:
            required_refs.add(record.prior_article_version_id)
        if record.prior_dossier_version_id is not None:
            required_refs.add(record.prior_dossier_version_id)
        if record.correction_case_version_id is not None:
            required_refs.add(record.correction_case_version_id)
        article_refs = {
            item.target_version_id
            for item in self.archive.get(
                record.article_version_id).submission.references}
        current_refs = {
            item.target_version_id
            for item in article.submission.references}
        if not required_refs <= article_refs or not required_refs <= current_refs:
            raise ArticleRouteError(
                "Routed Article does not preserve every route dependency")
        return record
