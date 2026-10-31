"""W18 synthetic pre-call gate, material permission and budget tests."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
from pathlib import Path
import tempfile
import unittest

from pydantic import ValidationError

from intelligence.archive import Archive, PermissionDenied
from intelligence.contracts import (MaterialUse, ObjectKind, PermissionState, ReferenceUse,
                                    Representation, RightsBasis, RightsGrant, Scope, ScopeMode,
                                    UsePermission, ValidityMode, VersionReference,
                                    VersionSubmission)
from intelligence.gating import (AdmissionMode, BudgetEnvelope, BudgetLedger, BudgetLine,
                                 CapabilityAdmission, GatingError, PreCallGate,
                                 ReservationEstimate)
from intelligence.operations import (AdapterDescriptor, AdapterReturn, CostObservation,
                                     ObservationKind, OperationKind, OperationRequest,
                                     OperationStatus, UsageObservation)

AT=datetime(2026,10,25,0,0,tzinfo=timezone.utc)
SPEC="a"*64
BODY=b"Owned synthetic W18 gate fixture\n"
RESULT=b"Owned actual gated result\n"


def permission(use, *, restricted=True):
    return UsePermission(use=use,state=PermissionState.ALLOWED,
        validity=ValidityMode.OPEN_ENDED,
        territories=Scope(mode=ScopeMode.LIST,values=("NZ",))
            if restricted else Scope(mode=ScopeMode.ANY),
        providers=Scope(mode=ScopeMode.LIST,values=("fixture-provider",))
            if restricted else Scope(mode=ScopeMode.ANY),
        content_scope=Scope(mode=ScopeMode.ANY),
        conditions_satisfied=True)


class FakeAdapter:
    def __init__(self, *, result=None, descriptor_max_retries=1):
        self.result=result
        self.calls=0
        self.descriptor_max_retries=descriptor_max_retries

    def descriptor(self):
        return AdapterDescriptor(tool_id="fixture-tool",tool_version="1.2.3",
            provider_id="fixture-provider",
            max_internal_retries=self.descriptor_max_retries)

    def invoke(self, operation, payload):
        self.calls+=1
        return self.result


class PreCallGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.archive=Archive(Path(self.temp.name)/"archive");self.addCleanup(self.archive.close)
        self.internal=self.rights("RIGHTS-INTERNAL",uses={MaterialUse.INDEX,MaterialUse.STORE_BODY})
        self.material_rights=self.rights("RIGHTS-MATERIAL",
            uses={MaterialUse.INDEX,MaterialUse.STORE_BODY,MaterialUse.MODEL_PROCESS},
            structured={
                MaterialUse.STORE_BODY:permission(MaterialUse.STORE_BODY,restricted=False),
                MaterialUse.MODEL_PROCESS:permission(MaterialUse.MODEL_PROCESS),
            })
        self.task=self.archive.append(VersionSubmission(
            object_id="TASK-W18",version_id="TASK-W18-v001",kind=ObjectKind.TASK,
            title="W18 task",spec_sha256=SPEC,created_at=AT,rights=self.internal,
            representation=Representation.FULL_BODY),BODY)
        self.material=self.archive.append(VersionSubmission(
            object_id="SOURCE-W18",version_id="SOURCE-W18-v001",kind=ObjectKind.DOCUMENT,
            title="W18 material",spec_sha256=SPEC,created_at=AT,rights=self.material_rights,
            representation=Representation.FULL_BODY),BODY)
        self.review=self.archive.append(VersionSubmission(
            object_id="REVIEW-W18",version_id="REVIEW-W18-v001",kind=ObjectKind.REVIEW,
            title="Capability review",spec_sha256=SPEC,created_at=AT,rights=self.internal,
            representation=Representation.FULL_BODY,
            references=(VersionReference(target_version_id="TASK-W18-v001",
                use=ReferenceUse.REVIEW_OF,locator="exact task"),)),BODY)
        self.gate=PreCallGate(self.archive,self.internal)
        self.budget=self.budget_envelope(cost="1.00",calls=10)
        self.gate.create_budget(self.budget)
        self.admission=self.capability_admission()
        self.gate.append_admission(self.admission)

    @staticmethod
    def rights(rights_id, *, uses, structured=None):
        structured=dict(structured or {})
        if (MaterialUse.STORE_BODY in uses
                and MaterialUse.STORE_BODY not in structured):
            structured[MaterialUse.STORE_BODY]=permission(
                MaterialUse.STORE_BODY,restricted=False)
        return RightsGrant(rights_id=rights_id,basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset(uses),
            evidence="Owned synthetic W18 gate fixture",checked_by="test fixture",
            checked_at=AT,permissions=tuple(structured.values()))

    def budget_envelope(self, *, cost="1.00", calls=10):
        return BudgetEnvelope(budget_id="BUDGET-W18",run_id="RUN-W18",
            task_version_id="TASK-W18-v001",
            quotas=(BudgetLine(metric="cost:USD",amount=Decimal(cost)),
                BudgetLine(metric="calls",amount=Decimal(calls))),
            valid_from=AT,valid_until=AT+timedelta(days=10),created_at=AT)

    def capability_admission(self, *, admission_id="ADMISSION-W18", external=True,
                             max_attempts=1,max_internal=1):
        return CapabilityAdmission(admission_id=admission_id,spec_sha256=SPEC,
            task_version_id="TASK-W18-v001",step_ids=("M18",),
            provider_id="fixture-provider",tool_id="fixture-tool",tool_version="1.2.3",
            configuration_sha256="c"*64,
            operation_kinds=(OperationKind.MODEL,),
            material_uses=(MaterialUse.MODEL_PROCESS,),territory="NZ",
            external_processing_allowed=external,budget_id="BUDGET-W18",
            max_attempts=max_attempts,max_internal_retries=max_internal,
            mode=AdmissionMode.APPROVED,review_version_id="REVIEW-W18-v001",
            valid_from=AT,valid_until=AT+timedelta(days=10),created_at=AT)

    @staticmethod
    def request(operation_id="OP-W18-1", *, key="LOGICAL-W18-1",
                provider="fixture-provider",max_attempts=1):
        return OperationRequest(operation_id=operation_id,idempotency_key=key,run_id="RUN-W18",
            task_version_id="TASK-W18-v001",step_id="M18",spec_sha256=SPEC,
            kind=OperationKind.MODEL,tool_id="fixture-tool",tool_version="1.2.3",
            provider_id=provider,configuration_sha256="c"*64,
            request_sha256=hashlib.sha256(BODY).hexdigest(),
            material_use=MaterialUse.MODEL_PROCESS,
            input_version_ids=("SOURCE-W18-v001",),attempt_number=1,
            max_attempts=max_attempts,created_at=AT)

    @staticmethod
    def estimate(operation_id="OP-W18-1", *, cost="0.10", basis=ObservationKind.ESTIMATED):
        return ReservationEstimate(operation_id=operation_id,basis=basis,
            lines=(BudgetLine(metric="cost:USD",amount=Decimal(cost)),
                BudgetLine(metric="calls",amount=Decimal("1"))))

    @staticmethod
    def success(cost=Decimal("0.03"), kind=ObservationKind.ACTUAL):
        return AdapterReturn(status=OperationStatus.SUCCEEDED,
            provider_request_id="PROVIDER-W18-1",response_body=RESULT,
            usage=(UsageObservation(metric="input_tokens",quantity=Decimal("12"),
                unit="token"),),
            cost=CostObservation(kind=kind,
                amount=None if kind is ObservationKind.UNKNOWN else cost,
                currency=None if kind is ObservationKind.UNKNOWN else "USD",
                basis="Owned gated adapter observation"),
            error_code=None,error_message=None,observed_internal_retries=0,
            started_at=AT+timedelta(seconds=1),ended_at=AT+timedelta(seconds=2))

    def test_admitted_call_reserves_then_settles_actual_cost(self):
        adapter=FakeAdapter(result=self.success())
        result=self.gate.execute("ADMISSION-W18",self.request(),adapter,BODY,
            self.estimate())
        self.assertEqual(adapter.calls,1)
        self.assertEqual(result.run.response_body,RESULT)
        self.assertEqual(result.material_use,MaterialUse.MODEL_PROCESS)
        self.assertFalse(result.manual_review_required)
        state=self.gate.ledger.state("BUDGET-W18")
        self.assertEqual(state.consumed["calls"],Decimal("1"))
        self.assertEqual(state.consumed["cost:usd"],Decimal("0.03"))
        self.assertEqual(state.reserved["calls"],Decimal("0"))
        self.assertEqual(state.remaining["cost:usd"],Decimal("0.97"))

    def test_controlled_trial_is_explicit_and_requires_manual_review(self):
        trial=self.capability_admission(admission_id="ADMISSION-TRIAL",
            max_attempts=1).model_copy(update={"mode":AdmissionMode.CONTROLLED_TRIAL})
        self.gate.append_admission(trial)
        adapter=FakeAdapter(result=self.success())
        result=self.gate.execute("ADMISSION-TRIAL",self.request(),adapter,BODY,
            self.estimate())
        self.assertEqual(adapter.calls,1)
        self.assertTrue(result.manual_review_required)

    def test_estimated_settlement_remains_distinct_from_actual(self):
        adapter=FakeAdapter(result=self.success(
            cost=Decimal("0.05"),kind=ObservationKind.ESTIMATED))
        result=self.gate.execute("ADMISSION-W18",self.request(),adapter,BODY,
            self.estimate())
        self.assertEqual(result.settlement.basis,ObservationKind.ESTIMATED)
        self.assertEqual(self.gate.ledger.state("BUDGET-W18").consumed["cost:usd"],
            Decimal("0.05"))

    def test_unknown_estimate_is_rejected_before_adapter(self):
        adapter=FakeAdapter(result=self.success())
        forged=ReservationEstimate.model_construct(operation_id="OP-W18-1",
            basis=ObservationKind.UNKNOWN,lines=self.estimate().lines)
        with self.assertRaises(ValidationError):
            self.gate.execute("ADMISSION-W18",self.request(),adapter,BODY,forged)
        self.assertEqual(adapter.calls,0)
        self.assertEqual(self.gate.ledger.state("BUDGET-W18").reserved["cost:usd"],
            Decimal("0"))

    def test_material_permission_and_external_flag_fail_before_adapter(self):
        denied_rights=self.rights("RIGHTS-NO-MODEL",
            uses={MaterialUse.INDEX,MaterialUse.STORE_BODY},
            structured={MaterialUse.STORE_BODY:permission(
                MaterialUse.STORE_BODY,restricted=False)})
        self.archive.append(VersionSubmission(
            object_id="SOURCE-NO-MODEL",version_id="SOURCE-NO-MODEL-v001",
            kind=ObjectKind.DOCUMENT,title="No model right",spec_sha256=SPEC,
            created_at=AT,rights=denied_rights,
            representation=Representation.FULL_BODY),BODY)
        request=self.request("OP-W18-1").model_copy(update={
            "input_version_ids":("SOURCE-NO-MODEL-v001",)})
        adapter=FakeAdapter(result=self.success())
        with self.assertRaises(PermissionDenied):
            self.gate.execute("ADMISSION-W18",request,adapter,BODY,self.estimate())
        self.assertEqual(adapter.calls,0)

        no_external=self.capability_admission(admission_id="ADMISSION-NO-EXTERNAL",
            external=False)
        self.gate.append_admission(no_external)
        with self.assertRaisesRegex(GatingError,"external"):
            self.gate.execute("ADMISSION-NO-EXTERNAL",self.request(),adapter,BODY,
                self.estimate())
        self.assertEqual(adapter.calls,0)

    def test_scope_retry_and_internal_retry_limits_fail_before_adapter(self):
        adapter=FakeAdapter(result=self.success())
        with self.assertRaisesRegex(GatingError,"provider/tool"):
            self.gate.execute("ADMISSION-W18",
                self.request(provider="other-provider"),adapter,BODY,self.estimate())
        with self.assertRaisesRegex(GatingError,"retry limit"):
            self.gate.execute("ADMISSION-W18",
                self.request(max_attempts=2),adapter,BODY,self.estimate())
        internal=FakeAdapter(result=self.success(),descriptor_max_retries=2)
        with self.assertRaisesRegex(GatingError,"internal retry"):
            self.gate.execute("ADMISSION-W18",self.request(),internal,BODY,
                self.estimate())
        wrong_use=self.request().model_copy(update={"material_use":MaterialUse.INDEX})
        with self.assertRaisesRegex(GatingError,"material use conflicts"):
            self.gate.execute("ADMISSION-W18",wrong_use,adapter,BODY,self.estimate())
        self.assertEqual(adapter.calls,0)
        self.assertEqual(internal.calls,0)

    def test_concurrent_calls_cannot_reserve_the_same_remaining_budget(self):
        budget=self.budget_envelope(cost="0.10",calls=2)
        budget=BudgetEnvelope.model_validate_json(budget.model_dump_json().replace(
            '"budget_id":"BUDGET-W18"','"budget_id":"BUDGET-CONCURRENT"'))
        self.gate.create_budget(budget)
        admission=self.capability_admission(
            admission_id="ADMISSION-CONCURRENT",max_attempts=2)
        admission=CapabilityAdmission.model_validate_json(
            admission.model_dump_json().replace(
                '"budget_id":"BUDGET-W18"','"budget_id":"BUDGET-CONCURRENT"'))
        self.gate.append_admission(admission)
        def worker(number):
            with Archive(self.archive.root) as archive:
                gate=PreCallGate(archive,self.internal)
                adapter=FakeAdapter(result=self.success(cost=Decimal("0.08")))
                try:
                    gate.execute("ADMISSION-CONCURRENT",
                        self.request(f"OP-CONCURRENT-{number}",
                            key=f"LOGICAL-CONCURRENT-{number}"),
                        adapter,BODY,self.estimate(f"OP-CONCURRENT-{number}",
                            cost="0.08"))
                    return "called" if adapter.calls==1 else "wrong"
                except (GatingError,PermissionDenied):
                    return "denied" if adapter.calls==0 else "called_then_denied"
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=sorted(pool.map(worker,(1,2)))
        self.assertEqual(outcomes,["called","denied"])

    def test_unknown_actual_cost_keeps_reservation_and_blocks_reuse(self):
        adapter=FakeAdapter(result=self.success(kind=ObservationKind.UNKNOWN))
        self.gate.execute("ADMISSION-W18",self.request(),adapter,BODY,self.estimate())
        state=self.gate.ledger.state("BUDGET-W18")
        self.assertEqual(state.reserved["cost:usd"],Decimal("0.10"))
        self.assertEqual(state.remaining["cost:usd"],Decimal("0.90"))
        self.assertEqual(len(state.unknown_reservations),1)
        with self.assertRaisesRegex(GatingError,"concurrent|Insufficient"):
            self.gate.ledger.reserve(
                "BUDGET-W18","ADMISSION-W18",
                self.request("OP-W18-2",key="LOGICAL-W18-2"),
                self.estimate("OP-W18-2",cost="0.95"),
                datetime.now(timezone.utc))


if __name__=="__main__":
    unittest.main()
