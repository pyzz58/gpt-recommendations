"""W20 owned-byte source adapter and candidate-index tests."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import tempfile
import unittest

from pydantic import ValidationError

from intelligence.archive import Archive
from intelligence.contracts import (MaterialUse, PermissionState, Representation, RightsBasis,
                                    RightsGrant, Scope, ScopeMode, UsePermission, ValidityMode,
                                    VersionSubmission)
from intelligence.sources import (AcquisitionMethod, AcquisitionStatus, CandidateStatus,
                                  ExcerptKind, GapCode, IndexStatus, PermissionStateW20,
                                  SourceAdapter, SourceAdapterController, SourceDescriptor,
                                  SourceType)

AT=datetime(2026,10,31,0,0,tzinfo=timezone.utc)
SPEC="a"*64
BODY=b"Owned synthetic source-adapter journal\n"
FEED=b'''<?xml version="1.0"?><rss version="2.0"><channel><title>Owned Feed</title><link>https://example.invalid/feed</link><description>Owned fixture</description>
<item><guid>owned-1</guid><title>Owned dated item</title><link>https://example.invalid/a</link><description>&lt;p&gt;Owned summary only.&lt;/p&gt;</description><pubDate>Fri, 30 Oct 2026 10:00:00 GMT</pubDate></item>
<item><guid>owned-2</guid><title>Owned undated item</title><link>https://example.invalid/b</link></item>
<item><guid>owned-3</guid><title>Owned item without link</title></item>
</channel></rss>'''
HTML=b'''<!doctype html><html><head><title>Owned HTML Article</title>
<meta property="og:title" content="Owned HTML Article">
<meta property="og:url" content="https://example.invalid/article">
<meta property="article:published_time" content="2026-10-30">
</head><body><article><h1>Owned HTML Article</h1>
<p>This is an owned synthetic article paragraph used solely for offline parsing and contains no third-party reporting.</p>
<p>A second owned paragraph lets the adapter form a short L1 excerpt, not an original-body archive.</p>
</article></body></html>'''
API=b'''{"items":[
{"id":"api-1","title":"Owned API item","url":"https://example.invalid/api-1","summary":"Owned API summary","published_at":"2026-10-30T09:00:00Z"},
{"id":"api-2","title":"Owned undated API item","url":"https://example.invalid/api-2"}
]}'''


class SourceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.archive=Archive(Path(self.temp.name)/"archive");self.addCleanup(self.archive.close)
        self.rights=RightsGrant(rights_id="RIGHTS-W20",basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({MaterialUse.INDEX,MaterialUse.STORE_BODY}),
            evidence="Owned synthetic W20 source index",checked_by="test fixture",
            checked_at=AT,permissions=(UsePermission(use=MaterialUse.STORE_BODY,
                state=PermissionState.ALLOWED,validity=ValidityMode.OPEN_ENDED,
                territories=Scope(mode=ScopeMode.ANY),providers=Scope(mode=ScopeMode.ANY),
                content_scope=Scope(mode=ScopeMode.ANY)),))
        self.adapter=SourceAdapter()

    def source(self, kind, source_id="SRC-OWNED-W20"):
        return SourceDescriptor(source_id=source_id,name="Owned fixture source",
            source_url="https://example.invalid/feed",source_type=kind,
            language="en",region="NZ",sector="fixture",ownership="Owned fixture owner",
            permission_state=PermissionStateW20.CLEARED,
            permission_evidence="Explicitly authored owned test bytes")

    def test_feed_candidates_keep_missing_date_and_link_gaps(self):
        index=self.adapter.parse(self.source(SourceType.FEED),FEED,
            acquired_at=AT,content_type="application/rss+xml",spec_sha256=SPEC)
        self.assertEqual(index.status,IndexStatus.PARTIAL)
        self.assertEqual(len(index.candidates),3)
        self.assertEqual(index.acquisition.raw_sha256,hashlib.sha256(FEED).hexdigest())
        self.assertEqual(index.acquisition.status,AcquisitionStatus.AVAILABLE)
        self.assertEqual(index.candidates[0].excerpt,"Owned summary only.")
        self.assertEqual(index.candidates[0].excerpt_kind,ExcerptKind.SOURCE_PROVIDED)
        self.assertEqual(index.candidates[0].region,"NZ")
        self.assertEqual(index.candidates[0].ownership,"Owned fixture owner")
        self.assertIn(GapCode.MISSING_DATE,{gap.code for gap in index.candidates[1].gaps})
        self.assertIn(GapCode.MISSING_LINK,{gap.code for gap in index.candidates[2].gaps})
        self.assertEqual(index.candidates[2].status,CandidateStatus.NEEDS_CHECK)
        self.assertFalse(index.automatic_discovery_verified)

    def test_html_adapter_returns_short_extracted_excerpt_not_full_archive(self):
        index=self.adapter.parse(self.source(SourceType.HTML),HTML,
            acquired_at=AT,content_type="text/html",spec_sha256=SPEC)
        self.assertEqual(index.status,IndexStatus.SUCCESS)
        candidate=index.candidates[0]
        self.assertEqual(candidate.title,"Owned HTML Article")
        self.assertEqual(candidate.original_url,"https://example.invalid/article")
        self.assertEqual(candidate.excerpt_kind,ExcerptKind.EXTRACTED)
        self.assertLessEqual(len(candidate.excerpt),500)
        self.assertNotIn("synthetic source-adapter journal",candidate.excerpt)
        self.assertEqual(candidate.published_at.precision.value,"DATE")
        self.assertEqual(candidate.evidence_status,"L1_CLUE_ONLY")

    def test_json_api_items_do_not_invent_summary_from_title(self):
        index=self.adapter.parse(self.source(SourceType.JSON_API),API,
            acquired_at=AT,content_type="application/json",spec_sha256=SPEC)
        self.assertEqual(len(index.candidates),2)
        self.assertEqual(index.candidates[0].excerpt,"Owned API summary")
        self.assertIsNone(index.candidates[1].excerpt)
        self.assertIn(GapCode.MISSING_DATE,{gap.code for gap in index.candidates[1].gaps})

    def test_unavailable_and_malformed_sources_are_explicit_failed_indexes(self):
        unavailable=self.adapter.parse(self.source(SourceType.FEED),b"",
            acquired_at=AT,content_type="application/rss+xml",spec_sha256=SPEC)
        self.assertEqual(unavailable.status,IndexStatus.FAILED)
        self.assertEqual(unavailable.candidates,())
        self.assertEqual(unavailable.acquisition.status,AcquisitionStatus.UNAVAILABLE)
        self.assertEqual(unavailable.gaps[0].code,GapCode.SOURCE_UNAVAILABLE)
        malformed=self.adapter.parse(self.source(SourceType.JSON_API),b"{not-json",
            acquired_at=AT,content_type="application/json",spec_sha256=SPEC)
        self.assertEqual(malformed.status,IndexStatus.FAILED)
        self.assertEqual(malformed.acquisition.status,AcquisitionStatus.PARSE_FAILED)
        self.assertEqual(malformed.acquisition.raw_sha256,
            hashlib.sha256(b"{not-json").hexdigest())
        self.assertEqual(malformed.gaps[0].code,GapCode.PARSE_ERROR)

    def test_uncleared_permission_cannot_be_constructed_and_manual_probe_is_not_discovery(self):
        with self.assertRaises(ValidationError):
            SourceDescriptor(source_id="SRC-NOT-CLEARED",name="Not cleared",
                source_url="https://example.invalid/no",source_type=SourceType.HTML,
                permission_state=PermissionStateW20.NOT_CLEARED,
                permission_evidence="Terms not reviewed")
        index=self.adapter.parse(self.source(SourceType.FEED),FEED,
            acquired_at=AT,content_type="application/rss+xml",
            method=AcquisitionMethod.MANUAL_PROBE,spec_sha256=SPEC)
        self.assertEqual(index.acquisition.method,AcquisitionMethod.MANUAL_PROBE)
        self.assertFalse(index.automatic_discovery_verified)
        self.assertIn("Single supplied feed",index.coverage_note)

    def test_candidate_index_roundtrips_through_shared_archive(self):
        index=self.adapter.parse(self.source(SourceType.FEED),FEED,
            acquired_at=AT,content_type="application/rss+xml",spec_sha256=SPEC)
        controller=SourceAdapterController(self.archive,self.rights)
        stored=controller.append_index(index)
        self.assertEqual(stored.submission.kind.value,"CandidateIndex")
        loaded=controller.load_index(index.index_id)
        self.assertEqual(loaded.model_dump(mode="json"),index.model_dump(mode="json"))
        self.assertFalse(loaded.automatic_discovery_verified)


if __name__=="__main__":
    unittest.main()
