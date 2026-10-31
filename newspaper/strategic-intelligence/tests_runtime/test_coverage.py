"""W22 independent reference-plan and coverage-gap tests."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from pydantic import ValidationError

from intelligence.archive import Archive
from intelligence.contracts import (MaterialUse, PermissionState, Precision, Representation,
                                    RightsBasis, RightsGrant, Scope, ScopeMode, TimePoint,
                                    UsePermission, ValidityMode,
                                    VersionSubmission)
from intelligence.coverage import (CandidateCoverageDecision, CoverageAudit,
                                   CoverageBasis, CoverageComparator, CoverageController,
                                   CoverageError, CoverageGapKind, CoverageReferencePlan,
                                   EditorialDecision, ReferenceChannelAttempt,
                                   ReferenceChannelOutcome, ReferenceItem, ReferenceOrigin,
                                   ReferenceResult, SelectionCoverageSnapshot)
from intelligence.discovery import CandidateHint, EventClusterer, LineageRole
from intelligence.sources import (PermissionStateW20, SourceAdapter, SourceDescriptor,
                                  SourceType)

AT=datetime(2026,10,31,0,0,tzinfo=timezone.utc)
SPEC="a"*64
BODY=b"Owned synthetic coverage journal\n"


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.archive=Archive(Path(self.temp.name)/"archive");self.addCleanup(self.archive.close)
        self.rights=RightsGrant(rights_id="RIGHTS-W22",basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({MaterialUse.INDEX,MaterialUse.STORE_BODY}),
            evidence="Owned synthetic coverage journal",checked_by="test fixture",
            checked_at=AT,permissions=(UsePermission(use=MaterialUse.STORE_BODY,
                state=PermissionState.ALLOWED,validity=ValidityMode.OPEN_ENDED,
                territories=Scope(mode=ScopeMode.ANY),providers=Scope(mode=ScopeMode.ANY),
                content_scope=Scope(mode=ScopeMode.ANY)),))
        self.adapter=SourceAdapter()
        self.clusterer=EventClusterer()
        self.comparator=CoverageComparator()

    def batch(self, event_keys):
        source=SourceDescriptor(source_id="SRC-W22-POOL",name="Owned candidate source",
            source_url="https://example.invalid/pool",source_type=SourceType.JSON_API,
            language="en",region="NZ",sector="fixture",ownership="Owned owner",
            permission_state=PermissionStateW20.CLEARED,
            permission_evidence="Owned synthetic pool")
        raw=json.dumps({"items":[
            {"id":f"item-{index}","title":f"Owned event {event_key}",
             "url":f"https://example.invalid/{event_key}",
             "summary":f"Owned clue for {event_key}",
             "published_at":"2026-10-30T10:00:00Z"}
            for index,event_key in enumerate(event_keys)]}).encode()
        index=self.adapter.parse(source,raw,acquired_at=AT,
            content_type="application/json",spec_sha256=SPEC)
        hints=(CandidateHint(candidate_index_id=index.index_id,
            candidate_id=index.candidates[position].candidate_id,event_key=event_key,
            lineage_role=LineageRole.ORIGINAL,lineage_root_ids=(f"ORIGIN-{event_key}",),
            note="Owned synthetic event mapping")
            for position,event_key in enumerate(event_keys))
        proposal=self.clusterer.build((index,),tuple(hints),
            proposal_id="PROPOSAL-W22",spec_sha256=SPEC,created_at=AT)
        return index,proposal

    def plan(self, event_keys, *, basis=CoverageBasis.INDEPENDENT_REFERENCE,
             fixed_at=AT-timedelta(hours=2), channel_outcome=ReferenceChannelOutcome.AVAILABLE):
        channel=ReferenceChannelAttempt(channel_id="REF-CHANNEL-1",source_id="SRC-REF-1",
            method="Owned independent query fixture",attempted_at=fixed_at,
            outcome=channel_outcome,
            note="Owned reference query completed" if channel_outcome is ReferenceChannelOutcome.AVAILABLE
                else "Owned reference source unavailable")
        references=tuple(ReferenceItem(
            item_id=f"REF-{index}",title=f"Owned reference {event_key}",
            source_id="SRC-REF-1",source_url=f"https://example.invalid/reference/{event_key}",
            channel_id="REF-CHANNEL-1",origin=ReferenceOrigin.EXTERNAL_QUERY,
            observed_at=fixed_at, published_at=TimePoint(precision=Precision.DATE,value="2026-10-30"),
            region="NZ",language="en",domain="fixture",event_key=event_key,
            positive_or_undercovered=(index==0),priority_basis="Owned independent reference")
            for index,event_key in enumerate(event_keys))
        return CoverageReferencePlan(plan_id="PLAN-W22",spec_sha256=SPEC,basis=basis,
            fixed_at=fixed_at,created_at=fixed_at+timedelta(minutes=10),
            window_start=fixed_at-timedelta(days=2),window_end=fixed_at,
            scope_description="Owned NZ fixture references for the declared window",
            selection_viewed_at_fix=False,channels=(channel,),references=references,
            limitations=("No global coverage claim",))

    def selection(self, decisions):
        return SelectionCoverageSnapshot(snapshot_id="SELECTION-W22",
            proposal_id="PROPOSAL-W22",decisions=tuple(
                CandidateCoverageDecision(candidate_id=candidate_id,decision=decision,
                    reason=f"Owned {decision.value} reason",
                    alternative_title="Alternative title" if decision is
                        EditorialDecision.COVERED_UNDER_OTHER_TITLE else None)
                for candidate_id,decision in decisions),
            created_at=AT+timedelta(minutes=5))

    def test_covered_selected_reference_can_have_no_gap(self):
        index,proposal=self.batch(("EVENT-A",))
        selection=self.selection(((index.candidates[0].candidate_id,
            EditorialDecision.SELECTED),))
        audit=self.comparator.compare(self.plan(("EVENT-A",)),(index,),proposal,
            audit_id="AUDIT-W22-COVERED",created_at=AT+timedelta(minutes=10),
            selection=selection)
        self.assertEqual(audit.comparisons[0].result,ReferenceResult.COVERED_SELECTED)
        self.assertEqual(audit.gaps,())
        self.assertFalse(audit.global_recall_claim)

    def test_missing_and_editorial_outcome_categories_are_distinct(self):
        events=("DISCARD","WATCH","MATERIAL","MISSED","DUPLICATE")
        index,proposal=self.batch(events)
        candidates=list(index.candidates)
        selection=self.selection((
            (candidates[0].candidate_id,EditorialDecision.DISCARDED),
            (candidates[1].candidate_id,EditorialDecision.WATCH),
            (candidates[2].candidate_id,EditorialDecision.MATERIAL_GAP),
            (candidates[3].candidate_id,EditorialDecision.NOT_EVALUATED),
            (candidates[4].candidate_id,EditorialDecision.SELECTED),
        ))
        plan=self.plan(("DISCARD","WATCH","MATERIAL","MISSED","DUPLICATE","DUPLICATE","ABSENT"))
        audit=self.comparator.compare(plan,(index,),proposal,
            audit_id="AUDIT-W22-GAPS",created_at=AT+timedelta(minutes=10),
            selection=selection)
        results=[item.result for item in audit.comparisons]
        self.assertIn(ReferenceResult.EDITOR_DISCARDED,results)
        self.assertIn(ReferenceResult.IMMATURE,results)
        self.assertIn(ReferenceResult.MATERIAL_INSUFFICIENT,results)
        self.assertIn(ReferenceResult.CLUSTER_OR_FILTER_MISSED,results)
        self.assertIn(ReferenceResult.COVERED_SELECTED,results)
        self.assertIn(ReferenceResult.DUPLICATE_COVERAGE,results)
        self.assertIn(ReferenceResult.NOT_DISCOVERED,results)
        kinds={item.kind for item in audit.gaps}
        self.assertIn(CoverageGapKind.NOT_DISCOVERED_IN_SCOPE,kinds)
        self.assertIn(CoverageGapKind.EDITOR_DISCARDED,kinds)
        self.assertIn(CoverageGapKind.DUPLICATE_COVERAGE,kinds)

    def test_source_outage_is_not_recorded_as_no_important_event(self):
        index,proposal=self.batch(("EVENT-A",))
        plan=self.plan(("EVENT-MISSING",),channel_outcome=ReferenceChannelOutcome.UNAVAILABLE)
        audit=self.comparator.compare(plan,(index,),proposal,
            audit_id="AUDIT-W22-OUTAGE",created_at=AT+timedelta(minutes=10))
        outage=[item for item in audit.gaps
                if item.kind is CoverageGapKind.SOURCE_UNAVAILABLE]
        self.assertEqual(len(outage),1)
        self.assertEqual(outage[0].channel_id,"REF-CHANNEL-1")
        self.assertIn("do not infer",outage[0].next_action)

    def test_domain_quota_and_selection_copied_references_are_rejected(self):
        with self.assertRaises(ValidationError):
            self.plan(("EVENT-A",),basis=CoverageBasis.DOMAIN_QUOTA)
        plan=self.plan(("EVENT-A",))
        copied=plan.references[0].model_copy(update={"origin":ReferenceOrigin.COPIED_FROM_SELECTION})
        with self.assertRaises(ValidationError):
            ReferenceItem.model_validate_json(copied.model_dump_json())

    def test_reference_plan_must_precede_candidate_view_and_archives_roundtrip(self):
        index,proposal=self.batch(("EVENT-A",))
        late=self.plan(("EVENT-A",),fixed_at=AT+timedelta(minutes=1))
        with self.assertRaisesRegex(CoverageError,"fixed before"):
            self.comparator.compare(late,(index,),proposal,
                audit_id="AUDIT-LATE",created_at=AT+timedelta(minutes=5))
        plan=self.plan(("EVENT-A",))
        audit=self.comparator.compare(plan,(index,),proposal,
            audit_id="AUDIT-W22-SAVE",created_at=AT+timedelta(minutes=10))
        controller=CoverageController(self.archive,self.rights)
        controller.append_plan(plan)
        controller.append_audit(audit)
        self.assertEqual(controller.load_plan("PLAN-W22").model_dump(mode="json"),
            plan.model_dump(mode="json"))
        self.assertEqual(controller.load_audit("AUDIT-W22-SAVE").model_dump(mode="json"),
            audit.model_dump(mode="json"))
        self.assertFalse(controller.load_audit("AUDIT-W22-SAVE").global_recall_claim)


if __name__=="__main__":
    unittest.main()
