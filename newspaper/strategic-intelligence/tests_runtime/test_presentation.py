"""W32 owned-fixture tests for reviewed continuous Edition rendering."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

from pydantic import ValidationError

from intelligence.adoption import StepState
from intelligence.archive import Archive
from intelligence.contracts import (ObjectKind, ReferenceUse, Representation,
                                    VersionReference, VersionSubmission)
from intelligence.editorial import (ArticleType, EditionPlacement,
                                    EditionPlacementProposal,
                                    EditorialController, PublicationBasis)
from intelligence.editorial_review import EditorialReviewController, ReviewDisposition
from intelligence.materials import ImportantUpdateCheck, UpdateAction
from intelligence.presentation import (EditionEntryRole,
                                       EditionPresentationController,
                                       EditionPresentationError,
                                       EditionRecord, EditionSourceRequest,
                                       ReviewedEditionEntry, SourceLink)
from intelligence.workflow import ResearchStep

AT = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)


def _version(prefix, identity):
    raw = json.dumps([prefix, identity], ensure_ascii=False,
                     sort_keys=True, separators=(",", ":")).encode()
    return prefix + hashlib.sha256(raw).hexdigest()[:32]


def _object(prefix, identity):
    raw = json.dumps([identity], ensure_ascii=False,
                     sort_keys=True, separators=(",", ":")).encode()
    return prefix + hashlib.sha256(raw).hexdigest()[:32]


class EditionPresentationTests(unittest.TestCase):
    def setUp(self):
        from tests_runtime.test_editorial_review import EditorialReviewTests
        self.rf = EditorialReviewTests(
            methodName="test_independent_review_pass_is_bound_to_actual_revision_and_w15")
        self.rf.setUp()
        self.addCleanup(self.rf.doCleanups)
        self.archive = self.rf.archive
        self.rights = self.rf.rights
        self.time = self.rf.time + timedelta(seconds=2)
        self.main_article = self.article(
            "ARTICLE-W32-MAIN",
            "# Bounded Commitment\n\n"
            "The commitment is documented, while execution remains unobserved.\n\n"
            "<script>alert('not executable')</script>")
        self.cover_article = self.article(
            "ARTICLE-W32-COVER",
            "# Owned Weekly Edition\n\n"
            "A reviewed cover explaining the bounded question of this edition.")
        self.update_check = self.make_update_check()
        self.proposal = self.make_proposal()
        self.main_review, self.main_case = self.review_article(
            self.main_article, "CASE-W32-MAIN", "REVIEW-W32-MAIN")
        self.cover_review, self.cover_case = self.review_article(
            self.cover_article, "CASE-W32-COVER", "REVIEW-W32-COVER")
        self.controller = EditionPresentationController(
            self.archive, self.rights, self.rf.reviewer,
            self.rf.reviewer.adoption)
        self.output_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.output_dir.cleanup)

    def article(self, object_id, text):
        self.time += timedelta(seconds=1)
        references = self.rf.article_references()
        return self.archive.append(VersionSubmission(
            schema_version=2, object_id=object_id,
            version_id=object_id + "-v001", kind=ObjectKind.ARTICLE,
            title=object_id, spec_sha256=self.rf.pf.revision.spec_sha256,
            created_at=self.time, rights=self.rights,
            representation=Representation.FULL_BODY,
            references=tuple(references)), text.encode())

    def make_update_check(self):
        self.time += timedelta(seconds=1)
        check = ImportantUpdateCheck(
            update_check_id="UPDATE-W32",
            material_version_id=self.rf.pf.fx.concept_version_id,
            theme_id="THEME-W29",
            spec_sha256=self.rf.pf.revision.spec_sha256,
            observed_source_intake_version_ids=(),
            observed_after_cutoff=False,
            affects_core_judgment=False,
            changes_object_scope_or_type=False,
            action=UpdateAction.NO_IMPORTANT_UPDATE,
            previous_knowledge_cutoff=AT,
            new_knowledge_cutoff=None,
            reason="Owned bounded update check",
            next_action="Proceed with the exact reviewed Article.",
            checked_by="OWNED-UPDATE-CHECK-W32",
            checked_at=self.time)
        version_id = _version("UPDATE-CHECK-", check.update_check_id)
        object_id = _object("UPDATE-CHECK-OBJECT-", check.update_check_id)
        return self.archive.append(VersionSubmission(
            schema_version=2, object_id=object_id,
            version_id=version_id,
            kind=ObjectKind.IMPORTANT_UPDATE_CHECK,
            title="Owned W32 update check",
            spec_sha256=check.spec_sha256, created_at=check.checked_at,
            rights=self.rights, representation=Representation.FULL_BODY),
            json.dumps(
                check.model_dump(mode="json"), ensure_ascii=False,
                sort_keys=True, separators=(",", ":")).encode())

    def make_proposal(self):
        self.time += timedelta(seconds=1)
        proposal = EditionPlacementProposal(
            edition_proposal_id="EDITION-PROPOSAL-W32",
            edition_id="EDITION-W32",
            spec_sha256=self.rf.pf.revision.spec_sha256,
            placements=(EditionPlacement(
                placement_id="PLACEMENT-W32-MAIN",
                topic_decision_id="TOPIC-DECISION-W32",
                research_admission_id="ADMISSION-W32",
                topic_id="TOPIC-W32",
                article_type=ArticleType.DEEP_THEME,
                publication_basis=PublicationBasis.CURRENT_WEEK,
                slot_order=2,
                editorial_role="Reviewed lead feature",
                reason="Owned W32 combination"),),
            combination_reason="Owned W32 reviewed edition composition",
            created_at=self.time)
        version_id = EditorialController._version(
            "EDITION-PROPOSAL-", proposal.edition_proposal_id)
        object_id = EditorialController._object(
            "EDITION-PROPOSAL-", proposal.edition_proposal_id)
        return self.archive.append(VersionSubmission(
            schema_version=2, object_id=object_id, version_id=version_id,
            kind=ObjectKind.EDITION_PLACEMENT_PROPOSAL,
            title="Owned W32 edition proposal",
            spec_sha256=proposal.spec_sha256,
            created_at=proposal.created_at,
            rights=self.rights, representation=Representation.FULL_BODY),
            json.dumps(
                proposal.model_dump(mode="json"), ensure_ascii=False,
                sort_keys=True, separators=(",", ":")).encode())

    def review_article(self, article, case_id, review_id):
        opened = self.rf.reviewer.open_case(self.rf.open_request(
            review_case_id=case_id,
            article_version_id=article.submission.version_id,
            inquiries=()))
        responded_at = max(self.time, opened.created_at) + timedelta(seconds=1)
        from intelligence.editorial_review import AuthorResponseRequest
        responded = self.rf.reviewer.respond(AuthorResponseRequest(
            review_case_version_id=opened.review_case_version_id,
            expected_current_case_version_id=opened.review_case_version_id,
            responder_id="AUTHOR-W31",
            article_version_id=article.submission.version_id,
            responses=(), note="No author change needed for this clean draft.",
            responded_at=responded_at))
        decided_at = responded_at + timedelta(seconds=1)
        from intelligence.editorial_review import FinalReviewRequest
        result = self.rf.reviewer.decide(FinalReviewRequest(
            review_case_version_id=responded.review_case_version_id,
            expected_current_case_version_id=responded.review_case_version_id,
            review_id=review_id,
            article_version_id=article.submission.version_id,
            reviewer_id="REVIEWER-W31",
            decision=ReviewDisposition.PASS,
            reviewed_scope=responded.reviewed_scope,
            closures=(),
            decision_reason="Owned clean review",
            remaining_limitations=(),
            expires_at=decided_at + timedelta(days=30),
            decided_at=decided_at))
        self.time = decided_at
        return result, responded

    def request(self, **updates):
        reviewed = self.rf.reviewer.load_review("REVIEW-W32-MAIN")
        created_at = max(self.time, reviewed.created_at) + timedelta(seconds=2)
        base = EditionSourceRequest(
            edition_id="EDITION-W32",
            composition_id="COMPOSITION-W32",
            spec_sha256=self.rf.pf.revision.spec_sha256,
            edition_proposal_id="EDITION-PROPOSAL-W32",
            important_update_check_version_id=(
                self.update_check.submission.version_id),
            coverage_start=AT,
            coverage_end=created_at,
            knowledge_cutoff=created_at,
            source_timezone="Pacific/Auckland",
            entries=(
                ReviewedEditionEntry(
                    entry_id="COVER",
                    role=EditionEntryRole.COVER, slot_order=1,
                    article_version_id=(
                        self.cover_article.submission.version_id),
                    review_version_id="REVIEW-W32-COVER",
                    adoption_decision_id=(
                        self.cover_review.adoption_decision_version_id),
                    title="Owned Weekly Edition",
                    required_scope=("W31_CONTENT_REVIEW", "B1_B2_C_ARTICLE")),
                ReviewedEditionEntry(
                    entry_id="MAIN",
                    role=EditionEntryRole.FEATURE, slot_order=2,
                    article_version_id=(
                        self.main_article.submission.version_id),
                    review_version_id="REVIEW-W32-MAIN",
                    adoption_decision_id=(
                        self.main_review.adoption_decision_version_id),
                    placement_id="PLACEMENT-W32-MAIN",
                    title="Bounded Commitment",
                    required_scope=("W31_CONTENT_REVIEW", "B1_B2_C_ARTICLE")),
            ),
            source_links=(SourceLink(
                label="Owned source",
                url="https://example.invalid/owned-source"),),
            output_path=str(
                Path(self.output_dir.name) / "edition.html"),
            created_at=created_at)
        return base.model_copy(update=updates)

    def test_composes_reviewed_readable_edition_without_publication_authority(self):
        result = self.controller.compose(self.request())
        self.assertEqual(
            Path(result.output_path),
            (Path(self.output_dir.name) / "edition.html").resolve())
        self.assertEqual(result.output_bytes, os.stat(result.output_path).st_size)
        self.assertEqual(stat.S_IMODE(os.stat(result.output_path).st_mode), 0o600)
        html = Path(result.output_path).read_text(encoding="utf-8")
        self.assertIn("<!doctype html>", html)
        self.assertIn("Bounded Commitment", html)
        self.assertIn("&lt;script&gt;alert", html)
        self.assertNotIn("<script>alert", html)
        self.assertIn("Owned source", html)
        record = self.controller.load_edition(result.edition_version_id)
        self.assertIs(record.content_review_required, True)
        self.assertIs(record.full_edition_review_required, True)
        self.assertIs(record.publication_authorized, False)
        self.assertIs(record.delivery_authorized, False)
        self.assertEqual(record.title, "Owned Weekly Edition")
        self.assertEqual(self.controller.compose(self.request()), result)

    def test_only_exact_passing_reviews_and_current_w15_decisions_are_used(self):
        entries = list(self.request().entries)
        entries[1] = entries[1].model_copy(update={
            "adoption_decision_id": "MISSING",
        })
        with self.assertRaisesRegex(EditionPresentationError, "current W15"):
            self.controller.compose(self.request(entries=tuple(entries)))

    def test_article_title_and_body_must_equal_reviewed_version(self):
        entries = list(self.request().entries)
        entries[1] = entries[1].model_copy(update={
            "title": "A different headline"})
        with self.assertRaisesRegex(EditionPresentationError, "differs from the reviewed H1"):
            self.controller.compose(self.request(entries=tuple(entries)))

    def test_feature_needs_exact_w23_placement_and_slot(self):
        request = self.request()
        entries = list(request.entries)
        entries[1] = entries[1].model_copy(update={"placement_id": "MISSING"})
        with self.assertRaisesRegex(EditionPresentationError, "absent from the W23"):
            self.controller.compose(self.request(entries=tuple(entries)))
        entries = list(request.entries)
        entries[1] = entries[1].model_copy(update={"slot_order": 3})
        with self.assertRaisesRegex(ValidationError, "continuous unique slots"):
            EditionSourceRequest.model_validate_json(
                self.request(entries=tuple(entries)).model_dump_json())

    def test_blocking_or_core_update_check_requires_return_not_layout(self):
        body = ImportantUpdateCheck.model_validate_json(
            self.archive.read_body(self.update_check.submission.version_id))
        changed = body.model_copy(update={
            "update_check_id": "UPDATE-W32-RETURN",
            "action": UpdateAction.RETURN_TO_W23,
            "checked_at": self.time + timedelta(seconds=1)})
        self.time += timedelta(seconds=1)
        stored = self.archive.append(VersionSubmission(
            schema_version=2,
            object_id=_object(
                "UPDATE-CHECK-OBJECT-", changed.update_check_id),
            version_id=_version("UPDATE-CHECK-", changed.update_check_id),
            kind=ObjectKind.IMPORTANT_UPDATE_CHECK,
            title="Owned update return",
            spec_sha256=changed.spec_sha256, created_at=self.time,
            rights=self.rights, representation=Representation.FULL_BODY),
            json.dumps(
                changed.model_dump(mode="json"), ensure_ascii=False,
                sort_keys=True, separators=(",", ":")).encode())
        with self.assertRaisesRegex(EditionPresentationError, "research/review return"):
            self.controller.compose(self.request(
                important_update_check_version_id=stored.submission.version_id))

    def test_source_links_reject_javascript_and_non_https_schemes(self):
        with self.assertRaises(ValidationError):
            SourceLink(label="Executable", url="javascript:alert(1)")
        with self.assertRaises(ValidationError):
            SourceLink(label="Insecure", url="http://example.invalid")

    def test_later_article_cannot_reuse_old_review_or_adoption(self):
        self.time += timedelta(seconds=1)
        later = self.archive.append(VersionSubmission(
            schema_version=2, object_id=self.main_article.submission.object_id,
            version_id="ARTICLE-W32-MAIN-v002",
            parent_version_id=self.main_article.submission.version_id,
            kind=ObjectKind.ARTICLE,
            title="ARTICLE-W32-MAIN",
            spec_sha256=self.main_article.submission.spec_sha256,
            created_at=self.time, rights=self.rights,
            representation=Representation.FULL_BODY,
            references=self.main_article.submission.references),
            b"# Bounded Commitment\n\nA later unreviewed draft.")
        entries = list(self.request().entries)
        entries[1] = entries[1].model_copy(update={
            "article_version_id": later.submission.version_id})
        with self.assertRaisesRegex(EditionPresentationError, "Review does not bind"):
            self.controller.compose(self.request(entries=tuple(entries)))

    def test_output_inside_git_and_existing_foreign_file_are_rejected(self):
        request = self.request()
        with self.assertRaises(Exception):
            self.controller.compose(request.model_copy(update={
                "output_path": str(Path.cwd() / "edition-should-not-exist.html")}))
        foreign = Path(self.output_dir.name) / "foreign.html"
        foreign.write_text("foreign", encoding="utf-8")
        foreign.chmod(0o600)
        with self.assertRaisesRegex(EditionPresentationError, "differs"):
            self.controller.compose(request.model_copy(update={
                "output_path": str(foreign)}))

    def test_concurrent_identical_render_is_idempotent(self):
        request = self.request()

        def worker(_):
            with Archive(self.archive.root) as archive:
                controller = EditionPresentationController(
                    archive, self.rights,
                    EditorialReviewController(archive, self.rights))
                try:
                    return controller.compose(request)
                except Exception as exc:
                    return exc

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(worker, range(2)))
        errors = [item for item in outcomes if isinstance(item, Exception)]
        self.assertFalse(errors, errors)
        self.assertEqual(outcomes[0], outcomes[1])

    def test_entry_order_and_reviewed_article_uniqueness_are_strict(self):
        request = self.request()
        entries = list(request.entries)
        entries[0] = entries[0].model_copy(update={"slot_order": 3})
        entries[1] = entries[1].model_copy(update={"slot_order": 2})
        with self.assertRaisesRegex(ValidationError, "continuous unique slots"):
            EditionSourceRequest.model_validate_json(
                request.model_copy(update={"entries": tuple(entries)})
                .model_dump_json())
        repeated = request.entries[1].model_copy(update={
            "entry_id": "MAIN-2", "slot_order": 3})
        with self.assertRaisesRegex(ValidationError, "cannot repeat"):
            EditionSourceRequest.model_validate_json(
                request.model_copy(update={
                    "entries": (*request.entries, repeated)})
                .model_dump_json())


if __name__ == "__main__":
    unittest.main()
