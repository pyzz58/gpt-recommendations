"""W32 continuous reviewed Article/Edition source and readable HTML output.

W32 never writes a second research narrative. It consumes exact PASS reviews and
current W15 adoptions for an actual reader Article and a separately reviewed
cover Article, composes the edition structure, and renders escaped reviewed text
through a restricted Jinja template. Generation is not publication or delivery.
"""
from __future__ import annotations

from enum import Enum
import hashlib
import html
from pathlib import Path
import re
import stat
from typing import Literal, Self
from urllib.parse import urlparse

from jinja2 import Environment, StrictUndefined
from markupsafe import Markup
from pydantic import AwareDatetime, Field, model_validator

from .adoption import AdoptionController, StepState
from .archive import (Archive, ArchiveError, Conflict, MissingVersion,
                      canonical, write_private_bytes)
from .contracts import (Contract, Digest, Identifier, NonBlank, ObjectKind,
                        ReferenceUse, Representation, RightsGrant, SourceTimes,
                        StoredVersion, VersionReference, VersionSubmission)
from .editorial import EditionPlacementProposal, EditorialController
from .editorial_review import (EditorialReviewController,
                               EditorialReviewDecision, ReviewDisposition)
from .materials import ImportantUpdateCheck, UpdateAction


class EditionEntryRole(str, Enum):
    COVER = "COVER"
    FEATURE = "FEATURE"
    UPDATE = "UPDATE"


class ReviewedEditionEntry(Contract):
    entry_id: Identifier
    role: EditionEntryRole
    slot_order: int = Field(ge=1)
    article_version_id: Identifier
    review_version_id: Identifier
    adoption_decision_id: Identifier
    placement_id: Identifier | None = None
    title: NonBlank
    required_scope: tuple[NonBlank, ...]

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if (not self.required_scope
                or len(self.required_scope) != len(set(self.required_scope))):
            raise ValueError(
                "Edition entry needs unique required review scope")
        if self.role is EditionEntryRole.FEATURE and self.placement_id is None:
            raise ValueError("Feature entry needs its W23 placement")
        if self.role is EditionEntryRole.COVER and self.placement_id is not None:
            raise ValueError("Cover entry cannot pretend to be a W23 placement")
        return self


class SourceLink(Contract):
    label: NonBlank
    url: NonBlank

    @model_validator(mode="after")
    def safe_url(self) -> Self:
        parsed = urlparse(self.url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Edition source links must be absolute HTTPS URLs")
        return self


class EditionSourceRequest(Contract):
    schema_version: Literal[1] = 1
    edition_id: Identifier
    composition_id: Identifier
    previous_version_id: Identifier | None = None
    spec_sha256: Digest
    edition_proposal_id: Identifier
    important_update_check_version_id: Identifier
    coverage_start: AwareDatetime
    coverage_end: AwareDatetime
    knowledge_cutoff: AwareDatetime
    source_timezone: NonBlank
    language: NonBlank = "zh-CN"
    entries: tuple[ReviewedEditionEntry, ...]
    source_links: tuple[SourceLink, ...] = ()
    output_path: NonBlank
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if not (
                self.coverage_start < self.coverage_end
                <= self.knowledge_cutoff <= self.created_at):
            raise ValueError(
                "Edition coverage, cutoff and creation times are not ordered")
        entry_ids = [item.entry_id for item in self.entries]
        slots = [item.slot_order for item in self.entries]
        if (not self.entries
                or len(entry_ids) != len(set(entry_ids))
                or len(slots) != len(set(slots))
                or sorted(slots) != list(range(1, len(slots) + 1))):
            raise ValueError(
                "Edition entries need unique IDs and continuous unique slots")
        roles = [item.role for item in self.entries]
        if roles.count(EditionEntryRole.COVER) != 1:
            raise ValueError("Edition needs exactly one reviewed cover entry")
        if EditionEntryRole.FEATURE not in roles:
            raise ValueError("Edition needs at least one adopted feature")
        if len({item.article_version_id for item in self.entries}) != len(
                self.entries):
            raise ValueError(
                "One composition cannot repeat an Article as a separate entry")
        link_keys = [(item.label.casefold(), item.url) for item in self.source_links]
        if len(link_keys) != len(set(link_keys)):
            raise ValueError("Duplicate edition source link")
        return self


class RenderedEditionEntry(Contract):
    entry_id: Identifier
    role: EditionEntryRole
    slot_order: int
    article_version_id: Identifier
    review_version_id: Identifier
    adoption_decision_id: Identifier
    placement_id: Identifier | None
    title: NonBlank
    article_body_sha256: Digest


class EditionRecord(Contract):
    schema_version: Literal[1] = 1
    edition_id: Identifier
    composition_id: Identifier
    edition_version_id: Identifier
    previous_version_id: Identifier | None
    spec_sha256: Digest
    title: NonBlank
    edition_proposal_id: Identifier
    important_update_check_version_id: Identifier
    coverage_start: AwareDatetime
    coverage_end: AwareDatetime
    knowledge_cutoff: AwareDatetime
    source_timezone: NonBlank
    language: NonBlank
    entries: tuple[RenderedEditionEntry, ...]
    source_links: tuple[SourceLink, ...]
    output_path: NonBlank
    output_sha256: Digest
    output_bytes: int = Field(gt=0)
    content_review_required: Literal[True] = True
    full_edition_review_required: Literal[True] = True
    publication_authorized: Literal[False] = False
    delivery_authorized: Literal[False] = False
    created_at: AwareDatetime


class EditionResult(Contract):
    edition_version_id: Identifier
    output_path: NonBlank
    output_sha256: Digest
    output_bytes: int


class EditionPresentationError(ArchiveError):
    """Composition/render failure, never full-edition review or publication."""


_CANONICAL_SPEC = (
    Path(__file__).resolve().parents[1] / "CANONICAL_SYSTEM_SPEC_V5.md")
_CANONICAL_TEMPLATE = re.compile(
    r"<!-- BEGIN EDITORIAL_HTML_TEMPLATE -->\n"
    r"```jinja2\n(.*?)\n```\n"
    r"<!-- END EDITORIAL_HTML_TEMPLATE -->", re.S)


def load_canonical_template(path: str | Path | None = None) -> str:
    source = Path(path or _CANONICAL_SPEC).read_text(encoding="utf-8")
    matches = _CANONICAL_TEMPLATE.findall(source)
    if len(matches) != 1:
        raise EditionPresentationError(
            "Canonical Edition template block is missing or duplicated")
    return matches[0]


def _digest(value) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _version(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([prefix, identity]).encode()).hexdigest()[:32]


def _object(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([identity]).encode()).hexdigest()[:32]


def _title_and_body(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    first_index = next(
        (index for index, line in enumerate(lines) if line.strip()), None)
    if first_index is None:
        raise EditionPresentationError("Reviewed Article body is empty")
    first = lines[first_index].strip()
    match = re.fullmatch(r"#\s+(.+)", first)
    if match is None:
        raise EditionPresentationError(
            "Reviewed Article must start with an H1 title")
    body = "\n".join(lines[first_index + 1:]).strip()
    if not body:
        raise EditionPresentationError(
            "Reviewed Article needs body content after its title")
    return match.group(1).strip(), body


def _body_markup(text: str) -> Markup:
    blocks = []
    paragraph = []

    def flush():
        if paragraph:
            value = " ".join(part.strip() for part in paragraph).strip()
            if value:
                blocks.append("<p>" + html.escape(value, quote=True) + "</p>")
            paragraph.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        heading = re.fullmatch(r"(#{2,4})\s+(.+)", stripped)
        if heading:
            flush()
            level = len(heading.group(1))
            blocks.append(
                f"<h{level}>"
                + html.escape(heading.group(2).strip(), quote=True)
                + f"</h{level}>")
        else:
            paragraph.append(line)
    flush()
    return Markup("\n".join(blocks))


class EditionPresentationController:
    def __init__(self, archive: Archive, rights: RightsGrant,
                 reviewer: EditorialReviewController | None = None,
                 adoption: AdoptionController | None = None,
                 template_text: str | None = None):
        if not isinstance(archive, Archive):
            raise TypeError("EditionPresentationController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError(
                "EditionPresentationController requires an internal journal grant")
        self.archive = archive
        self.rights = rights
        self.reviewer = reviewer or EditorialReviewController(archive, rights)
        self.adoption = adoption or AdoptionController(archive, rights)
        self.editorial = EditorialController(archive, rights)
        self.jinja = Environment(
            autoescape=True, undefined=StrictUndefined,
            loader=None, auto_reload=False)
        self.template = self.jinja.from_string(
            template_text or load_canonical_template())

    @staticmethod
    def _current(stored: StoredVersion, latest: StoredVersion | None,
                 label: str) -> None:
        if latest is None or latest.submission.version_id != stored.submission.version_id:
            raise EditionPresentationError(f"{label} version is stale")

    def _load_entry(self, entry: ReviewedEditionEntry, *,
                    proposal: EditionPlacementProposal,
                    at: AwareDatetime) -> tuple[
                        StoredVersion, EditorialReviewDecision, bytes, str]:
        article = self.archive.get(entry.article_version_id)
        if article.submission.kind is not ObjectKind.ARTICLE:
            raise EditionPresentationError(
                "Edition entry is not an Article")
        if article.submission.representation is not Representation.FULL_BODY:
            raise EditionPresentationError(
                "Edition entry needs a full reader Article")
        if article.body_retention_revoked:
            raise EditionPresentationError(
                "Edition entry Article was withdrawn")
        self._current(
            article, self.archive.latest(article.submission.object_id),
            "Article")
        body = self.archive.read_body(entry.article_version_id)
        try:
            article_text = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EditionPresentationError(
                "Reader Article is not valid UTF-8") from exc
        title, _ = _title_and_body(article_text)
        if entry.title != title:
            raise EditionPresentationError(
                "Edition title differs from the reviewed H1")
        review = self.reviewer.load_review(entry.review_version_id)
        if review.decision is not ReviewDisposition.PASS:
            raise EditionPresentationError(
                "Edition can only consume a PASS-reviewed Article")
        if review.article_version_id != entry.article_version_id:
            raise EditionPresentationError(
                "Review does not bind the selected Article version")
        if not set(entry.required_scope) <= set(review.reviewed_scope):
            raise EditionPresentationError(
                "Review scope does not cover this Edition use")
        if not self.adoption.is_current(
                entry.adoption_decision_id, at):
            raise EditionPresentationError(
                "Edition entry has no current W15 adoption")
        decision = self.adoption.load(entry.adoption_decision_id)
        if (decision.state is not StepState.READY
                or decision.subject_version_id != entry.article_version_id
                or decision.review_version_id != entry.review_version_id):
            raise EditionPresentationError(
                "W15 decision does not adopt this exact reviewed Article")
        if not self.adoption.authorizes(
                entry.adoption_decision_id, entry.required_scope, at):
            raise EditionPresentationError(
                "W15 decision does not authorize this Edition use scope")
        if entry.role is EditionEntryRole.FEATURE:
            placement = next(
                (item for item in proposal.placements
                 if item.placement_id == entry.placement_id), None)
            if placement is None:
                raise EditionPresentationError(
                    "Feature entry is absent from the W23 placement proposal")
            if placement.slot_order != entry.slot_order:
                raise EditionPresentationError(
                    "Feature entry order differs from its W23 placement")
        return article, review, body, article_text

    def compose(self, request: EditionSourceRequest) -> EditionResult:
        if not isinstance(request, EditionSourceRequest):
            raise TypeError("compose requires EditionSourceRequest")
        request = EditionSourceRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        proposal = self.editorial.load_current_edition_proposal(
            request.edition_proposal_id)
        if (proposal.spec_sha256 != request.spec_sha256
                or proposal.edition_id != request.edition_id):
            raise EditionPresentationError(
                "Edition proposal crosses identity or specification")
        proposal_version_id = EditorialController._version(
            "EDITION-PROPOSAL-", request.edition_proposal_id)
        proposal_stored = self.archive.get(proposal_version_id)
        # W26 update checks are shared records; identity and identity time are
        # checked locally so W32 need not create a second materials controller.
        update_stored = self.archive.get(
            request.important_update_check_version_id)
        if update_stored.submission.kind is not ObjectKind.IMPORTANT_UPDATE_CHECK:
            raise EditionPresentationError(
                "Edition update dependency is not an ImportantUpdateCheck")
        update_body = ImportantUpdateCheck.model_validate_json(
            self.archive.read_body(
                request.important_update_check_version_id))
        if (update_stored.submission.version_id
                != _version("UPDATE-CHECK-", update_body.update_check_id)
                or update_stored.submission.object_id
                != _object("UPDATE-CHECK-OBJECT-",
                           update_body.update_check_id)
                or update_stored.submission.created_at
                != update_body.checked_at
                or update_body.spec_sha256 != request.spec_sha256):
            raise EditionPresentationError(
                "ImportantUpdateCheck identity/specification mismatch")
        self._current(
            update_stored,
            self.archive.latest(update_stored.submission.object_id),
            "Important update check")
        if update_body.checked_at > request.created_at:
            raise EditionPresentationError(
                "Edition predates its important update check")
        if update_body.action not in (
                UpdateAction.NO_IMPORTANT_UPDATE,
                UpdateAction.RETAIN_OLD_CUTOFF_AND_RESCHEDULE):
            raise EditionPresentationError(
                "Edition update check requires research/review return, not pagination")
        if (update_body.affects_core_judgment
                and update_body.action is UpdateAction.NO_IMPORTANT_UPDATE):
            raise EditionPresentationError(
                "Core-affecting update cannot be marked no update")

        entries = []
        rendered = []
        feature_case = None
        for entry in sorted(request.entries, key=lambda item: item.slot_order):
            article, review, body, text = self._load_entry(
                entry, proposal=proposal, at=request.created_at)
            if review.created_at < update_body.checked_at:
                raise EditionPresentationError(
                    "Edition Article review predates the important update check")
            if review.created_at > request.created_at:
                raise EditionPresentationError(
                    "Edition predates its Article review")
            case_stored, case = self.reviewer.current_case(
                review.review_case_version_id)
            if entry.role is EditionEntryRole.FEATURE:
                if feature_case is None:
                    feature_case = case
                elif (case.theme_id != feature_case.theme_id
                      or case.revision_id != feature_case.revision_id):
                    raise EditionPresentationError(
                        "Features in one composition use different research revisions")
            title, main_text = _title_and_body(text)
            entries.append({
                "entry_id": entry.entry_id,
                "role": entry.role.value,
                "title": title,
                "body_html": _body_markup(main_text),
            })
            rendered.append(RenderedEditionEntry(
                entry_id=entry.entry_id, role=entry.role,
                slot_order=entry.slot_order,
                article_version_id=entry.article_version_id,
                review_version_id=entry.review_version_id,
                adoption_decision_id=entry.adoption_decision_id,
                placement_id=entry.placement_id, title=title,
                article_body_sha256=article.body_sha256))
        if feature_case is None:
            raise EditionPresentationError("Edition has no feature Article")
        if (update_body.theme_id != feature_case.theme_id):
            raise EditionPresentationError(
                "Important update check and Edition feature use different themes")
        cover = next(
            item for item in rendered if item.role is EditionEntryRole.COVER)
        coverage_text = (
            f"{request.coverage_start.isoformat()} — "
            f"{request.coverage_end.isoformat()} · "
            f"cutoff {request.knowledge_cutoff.isoformat()} · "
            f"{request.source_timezone}")
        document = self.template.render(
            language=request.language, title=cover.title,
            coverage_text=coverage_text, entries=entries,
            source_links=[item.model_dump(mode="json")
                          for item in request.source_links])
        output = document.encode("utf-8")
        output_sha = hashlib.sha256(output).hexdigest()
        object_id = _object("EDITION-OBJECT-", request.edition_id)
        edition_version_id = _version("EDITION-", canonical([
            request.edition_id, request.previous_version_id,
            _digest(request.model_dump(mode="json")), output_sha]))
        existing = None
        try:
            existing = self.archive.get(edition_version_id)
        except MissingVersion:
            pass
        latest = self.archive.latest(object_id)
        if existing is not None:
            body = self.archive.read_body(edition_version_id)
            existing_record = EditionRecord.model_validate_json(body)
            if (existing_record.edition_version_id != edition_version_id
                    or existing_record.output_sha256 != output_sha):
                raise EditionPresentationError(
                    "Existing Edition bytes differ from this composition")
            if (latest is None
                    or latest.submission.version_id != edition_version_id):
                raise EditionPresentationError(
                    "Existing Edition has been superseded")
            target = Path(request.output_path).expanduser().resolve(
                strict=False)
            try:
                mode = stat.S_IMODE(target.stat().st_mode)
                actual = target.read_bytes()
            except OSError as exc:
                raise EditionPresentationError(
                    "Existing Edition output cannot be verified") from exc
            if mode != 0o600 or actual != output:
                raise EditionPresentationError(
                    "Existing Edition output differs or is not private")
            return EditionResult(
                edition_version_id=edition_version_id,
                output_path=str(target), output_sha256=output_sha,
                output_bytes=len(output))
        if request.previous_version_id is None:
            if latest is not None:
                raise EditionPresentationError(
                    "Edition history requires previous version")
        elif (latest is None
              or latest.submission.version_id != request.previous_version_id):
            raise EditionPresentationError(
                "Edition previous version is not current")
        target = Path(request.output_path).expanduser().resolve(
            strict=False)
        try:
            written = write_private_bytes(target, output)
            created = True
        except FileExistsError:
            written = target
            created = False
            try:
                mode = stat.S_IMODE(written.stat().st_mode)
                actual = written.read_bytes()
            except OSError as exc:
                raise EditionPresentationError(
                    "Existing Edition output cannot be verified") from exc
            if mode != 0o600 or actual != output:
                raise EditionPresentationError(
                    "Existing Edition output differs or is not private")
        if existing is None:
            record = EditionRecord(
                edition_id=request.edition_id,
                composition_id=request.composition_id,
                edition_version_id=edition_version_id,
                previous_version_id=request.previous_version_id,
                spec_sha256=request.spec_sha256, title=cover.title,
                edition_proposal_id=request.edition_proposal_id,
                important_update_check_version_id=(
                    request.important_update_check_version_id),
                coverage_start=request.coverage_start,
                coverage_end=request.coverage_end,
                knowledge_cutoff=request.knowledge_cutoff,
                source_timezone=request.source_timezone,
                language=request.language, entries=tuple(rendered),
                source_links=request.source_links,
                output_path=str(written), output_sha256=output_sha,
                output_bytes=len(output), created_at=request.created_at)
            refs = [
                VersionReference(
                    target_version_id=proposal_version_id,
                    use=ReferenceUse.BASIS,
                    locator="exact W23 edition proposal"),
                VersionReference(
                    target_version_id=(
                        request.important_update_check_version_id),
                    use=ReferenceUse.BASIS,
                    locator="exact W26 important update check"),
                *(
                    VersionReference(
                        target_version_id=version_id,
                        use=ReferenceUse.SUPPORT,
                        locator=label)
                    for item in request.entries
                    for version_id, label in (
                        (item.article_version_id, "reviewed Article"),
                        (item.review_version_id, "passing Review"),
                        (item.adoption_decision_id, "W15 adoption"),
                    )
                ),
            ]
            submission = VersionSubmission(
                schema_version=2, object_id=object_id,
                version_id=edition_version_id,
                parent_version_id=request.previous_version_id,
                kind=ObjectKind.EDITION,
                title=f"edition source {request.edition_id}",
                spec_sha256=request.spec_sha256,
                created_at=request.created_at, source_times=SourceTimes(),
                rights=self.rights, representation=Representation.FULL_BODY,
                references=tuple(refs))
            record_bytes = canonical(record.model_dump(mode="json")).encode()
            expected = {
                object_id: latest.submission.version_id if latest else None,
                proposal_stored.submission.object_id:
                    proposal_stored.submission.version_id,
                update_stored.submission.object_id:
                    update_stored.submission.version_id,
            }
            for item in request.entries:
                for version_id in (
                        item.article_version_id, item.review_version_id,
                        item.adoption_decision_id):
                    stored = self.archive.get(version_id)
                    expected[stored.submission.object_id] = stored.submission.version_id
            try:
                self.archive.append(
                    submission, record_bytes, expected_current=expected)
            except Conflict:
                concurrent = self.archive.get(edition_version_id)
                concurrent_record = EditionRecord.model_validate_json(
                    self.archive.read_body(edition_version_id))
                if (concurrent.submission.kind is not ObjectKind.EDITION
                        or concurrent_record.output_sha256 != output_sha):
                    if created:
                        written.unlink(missing_ok=True)
                    raise
            except BaseException:
                if created:
                    written.unlink(missing_ok=True)
                raise
        return EditionResult(
            edition_version_id=edition_version_id,
            output_path=str(written), output_sha256=output_sha,
            output_bytes=len(output))

    def load_edition(self, edition_version_id: str) -> EditionRecord:
        stored = self.archive.get(edition_version_id)
        if stored.submission.kind is not ObjectKind.EDITION:
            raise EditionPresentationError(
                "Requested version is not an Edition")
        record = EditionRecord.model_validate_json(
            self.archive.read_body(edition_version_id))
        if (record.edition_version_id != edition_version_id
                or stored.submission.spec_sha256 != record.spec_sha256
                or stored.submission.created_at != record.created_at):
            raise EditionPresentationError("Edition identity mismatch")
        return record
