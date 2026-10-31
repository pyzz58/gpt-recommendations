"""W33 owned-fixture tests for dual as-of history and knowledge reuse."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from intelligence.archive import Archive, PermissionDenied
from intelligence.contracts import (MaterialUse, ObjectKind, PermissionState,
                                    Precision, ReferenceUse, Representation,
                                    RightsBasis, RightsGrant, Scope, ScopeMode,
                                    SourceTimes, TimePoint, UseContext,
                                    UsePermission, ValidityMode,
                                    VersionReference, VersionSubmission)
from intelligence.history import (HistoryArchiveController,
                                  HistoryArchiveError, HistoryMode,
                                  HistoryQueryRequest, KnowledgeReuseRecord,
                                  KnowledgeReuseRequest, ReuseConclusion)

BASE = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)


class FixedDateTime(datetime):
    value = BASE

    @classmethod
    def now(cls, tz=None):
        return cls.value if tz is None else cls.value.astimezone(tz)


class HistoryArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Archive(Path(self.temp.name) / "archive")
        self.addCleanup(self.archive.close)
        self.rights = RightsGrant(
            rights_id="RIGHTS-W33", basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({
                MaterialUse.INDEX, MaterialUse.STORE_BODY,
                MaterialUse.MODEL_PROCESS}),
            evidence="Owned W33 history fixture", checked_by="test fixture",
            checked_at=BASE,
            permissions=tuple(UsePermission(
                use=use, state=PermissionState.ALLOWED,
                validity=ValidityMode.OPEN_ENDED,
                territories=Scope(mode=ScopeMode.ANY),
                providers=Scope(mode=ScopeMode.ANY),
                content_scope=Scope(mode=ScopeMode.ANY))
                for use in (
                    MaterialUse.STORE_BODY, MaterialUse.MODEL_PROCESS)))
        self.controller = HistoryArchiveController(
            self.archive, self.rights)

    @staticmethod
    def instant(value):
        return TimePoint(
            precision=Precision.INSTANT, value=value.isoformat(),
            source_timezone="UTC", provenance="owned fixture timestamp")

    def append_at(self, recorded_at, *, object_id, version_id, kind,
                  body, published, title=None):
        FixedDateTime.value = recorded_at
        latest = self.archive.latest(object_id)
        with patch("intelligence.archive.datetime", FixedDateTime):
            return self.archive.append(VersionSubmission(
                schema_version=2, object_id=object_id, version_id=version_id,
                parent_version_id=(
                    latest.submission.version_id if latest else None),
                kind=kind, title=title or object_id,
                spec_sha256="a" * 64, created_at=recorded_at,
                source_times=SourceTimes(published=published),
                rights=self.rights,
                representation=Representation.FULL_BODY),
                body.encode())

    def context(self, at):
        return UseContext(
            at=at, provider="owned-local", territory="NZ",
            content=("owned-w33",))

    def query(self, object_id, mode, at, **updates):
        return self.controller.query(HistoryQueryRequest(
            query_id=f"QUERY-{mode.value}",
            object_id=object_id, mode=mode,
            at=None if mode is HistoryMode.CURRENT else at,
            intended_use=MaterialUse.MODEL_PROCESS,
            use_context=self.context(at),
            include_body=True, created_at=at, **updates))

    def three_versions(self):
        self.append_at(
            BASE + timedelta(days=1),
            object_id="THEME-HISTORY",
            version_id="THEME-HISTORY-v001", kind=ObjectKind.THESIS,
            body="Original January first wording",
            published=self.instant(BASE))
        self.append_at(
            BASE + timedelta(days=7),
            object_id="THEME-HISTORY",
            version_id="THEME-HISTORY-v002", kind=ObjectKind.THESIS,
            body="Later January fifth explanation",
            published=self.instant(BASE + timedelta(days=4)))
        self.append_at(
            BASE + timedelta(days=10),
            object_id="THEME-HISTORY",
            version_id="THEME-HISTORY-v003", kind=ObjectKind.THESIS,
            body="Later-recorded correction of a January third publication",
            published=self.instant(BASE + timedelta(days=2)))
        return BASE + timedelta(days=3)

    def test_known_and_public_as_of_are_isolated(self):
        at = self.three_versions()
        known = self.query(
            "THEME-HISTORY", HistoryMode.KNOWN_TO_SYSTEM_AS_OF, at)
        public = self.query(
            "THEME-HISTORY", HistoryMode.PUBLICLY_AVAILABLE_AS_OF, at)
        self.assertEqual(
            known.selected.version_id, "THEME-HISTORY-v001")
        self.assertEqual(
            known.known_to_system_version_id, "THEME-HISTORY-v001")
        self.assertFalse(known.system_unknown_at_as_of)
        self.assertEqual(
            known.body_text, "Original January first wording")
        self.assertEqual(
            public.selected.version_id, "THEME-HISTORY-v003")
        self.assertEqual(
            public.known_to_system_version_id, "THEME-HISTORY-v001")
        self.assertTrue(public.system_unknown_at_as_of)
        self.assertIn(
            "unknown to the system at as-of",
            " ".join(public.limitations))
        self.assertIn(
            "THEME-HISTORY-v002", known.later_version_ids)
        self.assertIn(
            "THEME-HISTORY-v003", known.later_version_ids)
        self.assertEqual(
            known.current_version_id, "THEME-HISTORY-v003")

    def test_current_returns_latest_body_without_authorizing_current_use(self):
        self.three_versions()
        current = self.query(
            "THEME-HISTORY", HistoryMode.CURRENT, BASE + timedelta(days=12))
        self.assertEqual(
            current.selected.version_id, "THEME-HISTORY-v003")
        self.assertEqual(
            current.current_version_id, "THEME-HISTORY-v003")
        self.assertTrue(current.body_available)
        self.assertIs(current.current_use_authorized, False)

    def test_event_before_publication_is_not_available_in_either_mode(self):
        self.append_at(
            BASE + timedelta(days=6),
            object_id="LATE-PUBLICATION",
            version_id="LATE-PUBLICATION-v001", kind=ObjectKind.DOCUMENT,
            body="The event occurred earlier",
            published=self.instant(BASE + timedelta(days=5)))
        at = BASE + timedelta(days=2)
        for mode in (
                HistoryMode.KNOWN_TO_SYSTEM_AS_OF,
                HistoryMode.PUBLICLY_AVAILABLE_AS_OF):
            with self.subTest(mode=mode):
                result = self.query("LATE-PUBLICATION", mode, at)
                self.assertIsNone(result.selected)
                self.assertFalse(result.body_available)

    def test_date_precision_does_not_invent_midnight(self):
        published = TimePoint(
            precision=Precision.DATE, value="2026-01-02",
            source_timezone="Pacific/Auckland",
            provenance="owned date-only publication")
        self.append_at(
            BASE + timedelta(days=3),
            object_id="DATE-PUBLICATION",
            version_id="DATE-PUBLICATION-v001", kind=ObjectKind.BACKGROUND,
            body="Date-only source", published=published)
        same_day = datetime(
            2026, 1, 2, 0, 0, tzinfo=timezone.utc)
        after_day = datetime(
            2026, 1, 3, 12, 0, tzinfo=timezone.utc)
        unavailable = self.query(
            "DATE-PUBLICATION",
            HistoryMode.PUBLICLY_AVAILABLE_AS_OF, same_day)
        available = self.query(
            "DATE-PUBLICATION",
            HistoryMode.PUBLICLY_AVAILABLE_AS_OF, after_day)
        self.assertIsNone(unavailable.selected)
        self.assertEqual(
            available.selected.version_id, "DATE-PUBLICATION-v001")

    def test_public_later_record_is_not_merged_into_known_result(self):
        at = self.three_versions()
        known = self.query(
            "THEME-HISTORY", HistoryMode.KNOWN_TO_SYSTEM_AS_OF, at)
        public = self.query(
            "THEME-HISTORY", HistoryMode.PUBLICLY_AVAILABLE_AS_OF, at)
        self.assertNotEqual(known.selected.version_id,
                            public.selected.version_id)
        self.assertFalse(known.system_unknown_at_as_of)
        self.assertTrue(public.system_unknown_at_as_of)
        self.assertEqual(
            public.body_text,
            "Later-recorded correction of a January third publication")

    def test_current_rights_can_withhold_body_but_history_remains(self):
        self.three_versions()
        at = BASE + timedelta(days=3)
        self.archive.revoke_rights(
            self.rights.rights_id, (MaterialUse.STORE_BODY,),
            "Owned W33 withdrawal")
        result = self.query(
            "THEME-HISTORY",
            HistoryMode.KNOWN_TO_SYSTEM_AS_OF, at)
        self.assertEqual(
            result.selected.version_id, "THEME-HISTORY-v001")
        self.assertFalse(result.body_available)
        self.assertIsNone(result.body_text)
        self.assertTrue(any(
            "withheld" in item for item in result.limitations))

    def test_unknown_publication_cannot_enter_exact_as_of(self):
        self.append_at(
            BASE + timedelta(days=1),
            object_id="UNKNOWN-PUBLICATION",
            version_id="UNKNOWN-PUBLICATION-v001", kind=ObjectKind.DOCUMENT,
            body="Unknown publication",
            published=TimePoint(
                precision=Precision.UNKNOWN,
                reason="Owned source never exposed a publication time"))
        result = self.query(
            "UNKNOWN-PUBLICATION",
            HistoryMode.PUBLICLY_AVAILABLE_AS_OF,
            BASE + timedelta(days=4))
        self.assertIsNone(result.selected)

    def test_index_rebuild_does_not_create_second_history_source(self):
        self.three_versions()
        before = self.query(
            "THEME-HISTORY", HistoryMode.CURRENT, BASE + timedelta(days=12))
        count = self.controller.rebuild_index()
        after = self.query(
            "THEME-HISTORY", HistoryMode.CURRENT, BASE + timedelta(days=12))
        self.assertGreaterEqual(count, 3)
        self.assertEqual(before.selected, after.selected)
        self.assertEqual(before.body_text, after.body_text)

    def test_knowledge_reuse_records_current_source_conditions_not_mastery(self):
        self.append_at(
            BASE + timedelta(days=1),
            object_id="CONCEPT-REUSE",
            version_id="CONCEPT-REUSE-v001", kind=ObjectKind.CONCEPT,
            body="Original commitment/execution distinction",
            published=self.instant(BASE))
        current = self.append_at(
            BASE + timedelta(days=2),
            object_id="CONCEPT-REUSE",
            version_id="CONCEPT-REUSE-v002", kind=ObjectKind.CONCEPT,
            body="Narrowed commitment/execution distinction",
            published=self.instant(BASE + timedelta(days=1)))
        article = self.append_at(
            BASE + timedelta(days=3),
            object_id="ARTICLE-REUSE",
            version_id="ARTICLE-REUSE-v001", kind=ObjectKind.ARTICLE,
            body="Owned current Article using the distinction",
            published=self.instant(BASE + timedelta(days=2)))
        evidence = self.append_at(
            BASE + timedelta(days=3),
            object_id="EVIDENCE-REUSE",
            version_id="EVIDENCE-REUSE-v001", kind=ObjectKind.EVIDENCE,
            body="Owned reuse evidence",
            published=self.instant(BASE + timedelta(days=2)))
        request = KnowledgeReuseRequest(
            reuse_id="REUSE-W33",
            source_version_id="CONCEPT-REUSE-v001",
            article_version_id=article.submission.version_id,
            theme_id="THEME-W33", spec_sha256="a" * 64,
            use_context=self.context(BASE + timedelta(days=4)),
            original_conditions=("Same actor and observation period",),
            current_conditions=(
                "Same actor and a different review period",
            ),
            changed_conditions=("The review period changed",),
            conclusion=ReuseConclusion.NARROWED,
            evidence_version_ids=(evidence.submission.version_id,),
            does_not_prove=(
                "Reuse does not prove execution or reader learning"),
            created_at=BASE + timedelta(days=4))
        record = self.controller.record_reuse(request)
        self.assertEqual(
            record.source_version_id, "CONCEPT-REUSE-v001")
        self.assertEqual(
            record.current_source_version_id,
            current.submission.version_id)
        self.assertIs(record.reader_state_recorded, False)
        self.assertEqual(
            record.evidence_version_ids,
            (evidence.submission.version_id,))
        loaded = KnowledgeReuseRecord.model_validate_json(
            self.archive.read_body(record.reuse_version_id))
        self.assertEqual(loaded.conclusion, ReuseConclusion.NARROWED)
        self.assertEqual(self.controller.record_reuse(request), record)

    def test_query_contract_requires_explicit_mode_time_and_index_boundary(self):
        with self.assertRaisesRegex(ValidationError, "explicit as-of"):
            HistoryQueryRequest(
                query_id="BAD-HISTORY", object_id="THEME-HISTORY",
                mode=HistoryMode.KNOWN_TO_SYSTEM_AS_OF,
                intended_use=MaterialUse.INDEX,
                use_context=self.context(BASE), created_at=BASE)
        with self.assertRaisesRegex(ValidationError, "INDEX"):
            HistoryQueryRequest(
                query_id="BAD-INDEX", object_id="THEME-HISTORY",
                mode=HistoryMode.CURRENT,
                intended_use=MaterialUse.INDEX,
                use_context=self.context(BASE), include_body=True,
                created_at=BASE)

    def test_transmission_link_uses_same_versioned_history(self):
        self.append_at(
            BASE + timedelta(days=1),
            object_id="TRANSMISSION-W33",
            version_id="TRANSMISSION-W33-v001",
            kind=ObjectKind.TRANSMISSION_LINK,
            body="First conditional transmission link",
            published=self.instant(BASE))
        self.append_at(
            BASE + timedelta(days=3),
            object_id="TRANSMISSION-W33",
            version_id="TRANSMISSION-W33-v002",
            kind=ObjectKind.TRANSMISSION_LINK,
            body="Second conditional transmission link",
            published=self.instant(BASE + timedelta(days=2)))
        result = self.query(
            "TRANSMISSION-W33",
            HistoryMode.KNOWN_TO_SYSTEM_AS_OF,
            BASE + timedelta(days=2))
        self.assertEqual(
            result.selected.version_id, "TRANSMISSION-W33-v001")
        self.assertEqual(
            result.current_version_id, "TRANSMISSION-W33-v002")


if __name__ == "__main__":
    unittest.main()
