"""W21 owned-candidate event clustering and exploration tests."""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from intelligence.archive import Archive
from intelligence.contracts import (MaterialUse, PermissionState, Representation, RightsBasis,
                                    RightsGrant, Scope, ScopeMode, UsePermission, ValidityMode,
                                    VersionSubmission)
from intelligence.discovery import (CandidateHint, ClusterStatus, DiscoveryReview,
                                    EventClusterController, EventClusterer,
                                    ExplorationReason, IndependenceStatus, LineageRole,
                                    MergeBasis)
from intelligence.sources import (PermissionStateW20, SourceAdapter, SourceDescriptor,
                                  SourceType)

AT=datetime(2026,10,31,0,0,tzinfo=timezone.utc)
SPEC="a"*64
BODY=b"Owned synthetic discovery journal\n"


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.archive=Archive(Path(self.temp.name)/"archive");self.addCleanup(self.archive.close)
        self.rights=RightsGrant(rights_id="RIGHTS-W21",basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({MaterialUse.INDEX,MaterialUse.STORE_BODY}),
            evidence="Owned synthetic discovery journal",checked_by="test fixture",
            checked_at=AT,permissions=(UsePermission(use=MaterialUse.STORE_BODY,
                state=PermissionState.ALLOWED,validity=ValidityMode.OPEN_ENDED,
                territories=Scope(mode=ScopeMode.ANY),providers=Scope(mode=ScopeMode.ANY),
                content_scope=Scope(mode=ScopeMode.ANY)),))
        self.adapter=SourceAdapter()
        self.clusterer=EventClusterer()

    def index(self, source_id, entries):
        source=SourceDescriptor(source_id=source_id,name="Owned discovery source",
            source_url=f"https://example.invalid/{source_id}",source_type=SourceType.JSON_API,
            language="en",region="NZ",sector="fixture",ownership="Owned owner",
            permission_state=PermissionStateW20.CLEARED,
            permission_evidence="Owned synthetic items")
        raw=json.dumps({"items":entries}).encode()
        return self.adapter.parse(source,raw,acquired_at=AT,
            content_type="application/json",spec_sha256=SPEC)

    @staticmethod
    def item(number, *, title=None, url=None, date="2026-10-30T10:00:00Z"):
        return {"id":f"item-{number}","title":title or f"Owned item {number}",
            "url":url or f"https://example.invalid/item-{number}",
            "summary":f"Owned summary {number}","published_at":date}

    def hint(self, index, candidate, *, role=LineageRole.UNKNOWN, roots=(),
             event_key=None, related=(), low_heat=False, original=None,
             duplicate=None):
        return CandidateHint(candidate_index_id=index.index_id,
            candidate_id=candidate.candidate_id,event_key=event_key,
            lineage_role=role,lineage_root_ids=tuple(roots),
            original_candidate_id=original,duplicate_of_candidate_id=duplicate,
            possible_related_candidate_ids=tuple(related),low_heat=low_heat,
            note="Owned synthetic lineage fixture")

    def review(self, indexes, hints, proposal_id="DISCOVERY-W21-001"):
        return self.clusterer.build(tuple(indexes),tuple(hints),
            proposal_id=proposal_id,spec_sha256=SPEC,created_at=AT)

    def test_ten_reposts_share_one_recorded_origin_not_ten_independent_sources(self):
        index=self.index("SRC-W21-REPOSTS",[self.item(i) for i in range(10)])
        hints=[]
        for i,candidate in enumerate(index.candidates):
            hints.append(self.hint(index,candidate,
                role=LineageRole.ORIGINAL if i==0 else LineageRole.REPOST,
                roots=("STORY-SHARED",),low_heat=(i==9),
                original=None if i==0 else index.candidates[0].candidate_id))
        review=self.review((index,),hints)
        self.assertEqual(len(review.candidate_ids),10)
        self.assertEqual(len(review.clusters),1)
        cluster=review.clusters[0]
        self.assertEqual(cluster.independence_status,IndependenceStatus.RECORDED)
        self.assertEqual(cluster.independent_origin_ids,("STORY-SHARED",))
        self.assertEqual(len(cluster.candidate_ids),10)
        self.assertIn(MergeBasis.SHARED_LINEAGE_ROOT,cluster.merge_basis)
        queued={item.candidate_id:item.reasons for item in review.exploration_queue}
        self.assertIn(ExplorationReason.LOW_HEAT_OR_SINGLE_SOURCE,
            queued[index.candidates[9].candidate_id])

    def test_explicit_event_updates_merge_while_possible_matches_stay_ambiguous(self):
        first=self.index("SRC-W21-A",[self.item(1,title="Original title")])
        second=self.index("SRC-W21-B",[self.item(2,title="Updated title")])
        a,b=first.candidates[0],second.candidates[0]
        review=self.review((first,second),(
            self.hint(first,a,role=LineageRole.ORIGINAL,roots=("ORIGIN-A",),
                event_key="EVENT-1"),
            self.hint(second,b,role=LineageRole.ORIGINAL,roots=("ORIGIN-B",),
                event_key="EVENT-1")))
        self.assertEqual(len(review.clusters),1)
        cluster=review.clusters[0]
        self.assertEqual(cluster.event_key,"EVENT-1")
        self.assertEqual(set(cluster.independent_origin_ids),{"ORIGIN-A","ORIGIN-B"})
        self.assertEqual(len(cluster.differences),2)
        self.assertIn("Updated title",cluster.differences[0]+cluster.differences[1])

        third=self.index("SRC-W21-C",[self.item(3,title="Possibly related")])
        fourth=self.index("SRC-W21-D",[self.item(4,title="Another possibility")])
        c,d=third.candidates[0],fourth.candidates[0]
        review2=self.review((third,fourth),(
            self.hint(third,c,event_key="EVENT-C",related=(d.candidate_id,)),
            self.hint(fourth,d,event_key="EVENT-D",related=(c.candidate_id,))),
            proposal_id="DISCOVERY-W21-AMBIGUOUS")
        self.assertEqual(len(review2.clusters),2)
        self.assertTrue(all(item.status is ClusterStatus.NEEDS_EDITOR
            for item in review2.clusters))
        self.assertTrue(any(ExplorationReason.AMBIGUOUS_POSSIBLE_MATCH
            in item.reasons for item in review2.exploration_queue))

    def test_exact_url_duplicate_does_not_infer_independence_or_drop_low_heat(self):
        first=self.index("SRC-W21-E",[self.item(5,url="https://example.invalid/same")])
        second=self.index("SRC-W21-F",[self.item(6,url="https://example.invalid/same")])
        a,b=first.candidates[0],second.candidates[0]
        review=self.review((first,second),(
            self.hint(first,a,low_heat=True),self.hint(second,b)))
        self.assertEqual(len(review.clusters),1)
        cluster=review.clusters[0]
        self.assertIn(MergeBasis.EXACT_URL,cluster.merge_basis)
        self.assertEqual(cluster.independence_status,IndependenceStatus.UNKNOWN)
        self.assertEqual(cluster.independent_origin_ids,())
        self.assertTrue(any(item.candidate_id==a.candidate_id
            and ExplorationReason.LOW_HEAT_OR_SINGLE_SOURCE in item.reasons
            for item in review.exploration_queue))

    def test_no_hints_never_forces_event_merge_and_all_candidates_survive(self):
        index=self.index("SRC-W21-NOHINT",[
            self.item(7,title="Similar headline"),
            self.item(8,title="Similar headline")])
        review=self.review((index,),())
        self.assertEqual(len(review.candidate_ids),2)
        self.assertEqual(len(review.clusters),2)
        self.assertEqual(len(review.exploration_queue),2)
        self.assertTrue(all(item.independence_status is IndependenceStatus.UNKNOWN
            for item in review.clusters))
        self.assertTrue(all(ClusterStatus.PROPOSED is item.status
            for item in review.clusters))

    def test_proposal_roundtrips_through_shared_archive_for_t03_review(self):
        index=self.index("SRC-W21-SAVE",[self.item(9)])
        candidate=index.candidates[0]
        review=self.review((index,),(
            self.hint(index,candidate,role=LineageRole.ORIGINAL,
                roots=("ORIGIN-SAVE",),event_key="EVENT-SAVE"),))
        controller=EventClusterController(self.archive,self.rights)
        stored=controller.append_proposal(review)
        self.assertEqual(stored.submission.kind.value,"EventClusterProposal")
        loaded=controller.load_proposal(review.proposal_id)
        self.assertEqual(loaded.model_dump(mode="json"),review.model_dump(mode="json"))
        self.assertEqual(loaded.clusters[0].differences,review.clusters[0].differences)


if __name__=="__main__":
    unittest.main()
