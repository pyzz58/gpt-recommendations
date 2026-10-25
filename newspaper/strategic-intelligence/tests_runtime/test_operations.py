"""W17 tool adapter identity, receipt and unresolved-outcome tests."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from intelligence.archive import Archive, Conflict
from intelligence.contracts import (MaterialUse, ObjectKind, Representation, RightsBasis,
                                    RightsGrant, VersionSubmission)
from intelligence.operations import (AdapterDescriptor, AdapterReturn, CostObservation,
                                     ObservationKind, OperationError, OperationJournal,
                                     OperationKind, OperationRequest, OperationStatus,
                                     ToolAdapterError, ToolResponse, UsageObservation)

AT=datetime(2026,10,25,0,0,tzinfo=timezone.utc)
SPEC="a"*64
BODY=b"Owned synthetic operation body\n"
RESULT=b"Actual adapter response bytes\n"
PROJECT=Path(__file__).resolve().parents[1]


class FakeAdapter:
    def __init__(self, result=None, error=None):
        self.result=result
        self.error=error
        self.calls=0

    def descriptor(self):
        return AdapterDescriptor(tool_id="fixture-tool",tool_version="1.2.3",
            provider_id="fixture-provider",max_internal_retries=1)

    def invoke(self, operation, payload):
        self.calls+=1
        if self.error is not None:
            raise self.error
        return self.result


class OperationJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.archive=Archive(Path(self.temp.name)/"archive");self.addCleanup(self.archive.close)
        self.rights=RightsGrant(rights_id="RIGHTS-OPERATIONS",basis=RightsBasis.OWN_WORK,
            allowed_uses=frozenset({MaterialUse.INDEX,MaterialUse.STORE_BODY}),
            evidence="Owned synthetic operation journal",checked_by="test fixture",checked_at=AT)
        self.journal=OperationJournal(self.archive,self.rights)
        self.task=self.archive.append(VersionSubmission(
            object_id="TASK-1",version_id="TASK-1-v001",kind=ObjectKind.TASK,title="Task",
            spec_sha256=SPEC,created_at=AT,rights=self.rights,
            representation=Representation.FULL_BODY),BODY)
        self.evidence=self.archive.append(VersionSubmission(
            object_id="EVIDENCE-1",version_id="EVIDENCE-1-v001",kind=ObjectKind.EVIDENCE,
            title="Evidence",spec_sha256=SPEC,created_at=AT,rights=self.rights,
            representation=Representation.FULL_BODY),BODY)

    def request(self, operation_id="OP-1", *, attempt=1, max_attempts=1,
                retry=None, expected=None, digest_value=None, tool_version="1.2.3",
                provider_id="fixture-provider"):
        return OperationRequest(operation_id=operation_id,idempotency_key="LOGICAL-OP-1",
            run_id="RUN-1",task_version_id="TASK-1-v001",step_id="T26",
            spec_sha256=SPEC,kind=OperationKind.SEARCH,tool_id="fixture-tool",
            tool_version=tool_version,provider_id=provider_id,
            configuration_sha256="c"*64,
            request_sha256=digest_value or hashlib.sha256(BODY).hexdigest(),
            input_version_ids=("EVIDENCE-1-v001",),attempt_number=attempt,max_attempts=max_attempts,
            retry_of_operation_id=retry,expected_previous_operation_id=expected,
            created_at=AT+timedelta(minutes=attempt))

    def success_return(self, *, retries=0):
        return AdapterReturn(status=OperationStatus.SUCCEEDED,provider_request_id="PROVIDER-REQ-1",
            response_body=RESULT,usage=(UsageObservation(metric="search_calls",quantity=Decimal("1"),unit="call"),),
            cost=CostObservation(kind=ObservationKind.ACTUAL,amount=Decimal("0.03"),currency="USD",
                basis="Fixture provider response"),
            error_code=None,error_message=None,observed_internal_retries=retries,
            started_at=AT+timedelta(seconds=1),ended_at=AT+timedelta(seconds=2))

    def test_success_records_exact_request_identity_and_actual_receipt(self):
        run=self.journal.run(self.request(),FakeAdapter(self.success_return()),BODY)
        self.assertEqual(run.response_body,RESULT)
        receipt=self.journal.receipt("OP-1")
        self.assertEqual(receipt.status,OperationStatus.SUCCEEDED)
        self.assertEqual(receipt.provider_request_id,"PROVIDER-REQ-1")
        self.assertEqual(receipt.cost.amount,Decimal("0.03"))
        self.assertEqual(receipt.source.value,"ADAPTER")
        self.assertEqual(receipt.result_sha256,hashlib.sha256(RESULT).hexdigest())
        self.assertEqual(self.archive.get("OP-1").submission.kind,ObjectKind.OPERATION_REQUEST)
        self.assertEqual(self.archive.get("RESULT-OP-1").submission.kind,ObjectKind.OPERATION_RECEIPT)

    def test_duplicate_success_is_not_invoked_again(self):
        adapter=FakeAdapter(self.success_return())
        self.journal.run(self.request(),adapter,BODY)
        with self.assertRaisesRegex(OperationError,"Retry does not bind"):
            self.journal.run(self.request("OP-2"),adapter,BODY)
        self.assertEqual(adapter.calls,1)

    def test_unknown_timeout_blocks_automatic_retry_until_reconciled(self):
        adapter=FakeAdapter(error=ToolAdapterError("provider accepted then timed out",
            provider_request_id="PROVIDER-REQ-UNKNOWN"))
        run=self.journal.run(self.request(),adapter,BODY)
        receipt=self.journal.receipt("OP-1")
        self.assertEqual(run.receipt.submission.version_id,"RESULT-OP-1")
        self.assertEqual(receipt.status,OperationStatus.UNKNOWN)
        self.assertEqual(receipt.provider_request_id,"PROVIDER-REQ-UNKNOWN")
        self.assertEqual(self.journal.summary("LOGICAL-OP-1").unknown_cost_attempts,1)
        with self.assertRaisesRegex(OperationError,"must be reconciled"):
            self.journal.run(self.request("OP-2",attempt=2,max_attempts=2,
                retry="OP-1",expected="OP-1"),FakeAdapter(self.success_return()),BODY)
        self.assertEqual(adapter.calls,1)

    def test_only_failed_operation_can_retry_with_same_request_identity(self):
        failed=AdapterReturn(status=OperationStatus.FAILED,provider_request_id="PROVIDER-REQ-FAILED",
            response_body=None,usage=(),cost=CostObservation(kind=ObservationKind.ACTUAL,
                amount=Decimal("0.01"),currency="USD",basis="Provider rejected request"),
            error_code="INVALID_INPUT",error_message="Rejected",observed_internal_retries=0,
            started_at=AT+timedelta(seconds=1),ended_at=AT+timedelta(seconds=2))
        self.journal.run(self.request(max_attempts=2),FakeAdapter(failed),BODY)
        retry=self.request("OP-2",attempt=2,max_attempts=2,retry="OP-1",expected="OP-1")
        second_adapter=FakeAdapter(self.success_return())
        self.journal.run(retry,second_adapter,BODY)
        self.assertEqual(second_adapter.calls,1)
        self.assertEqual(self.journal.receipt("OP-2").status,OperationStatus.SUCCEEDED)
        summary=self.journal.summary("LOGICAL-OP-1")
        self.assertEqual(summary.operation_ids,("OP-1","OP-2"))
        self.assertEqual(summary.statuses,(OperationStatus.FAILED,OperationStatus.SUCCEEDED))
        self.assertEqual(summary.actual_cost_by_currency,{"USD":Decimal("0.04")})
        self.assertEqual(summary.unknown_cost_attempts,0)
        self.assertEqual(summary.elapsed_seconds,Decimal("2"))
        query=subprocess.run([sys.executable,"-m","intelligence","--root",str(self.archive.root),
            "operation-summary","LOGICAL-OP-1"],cwd=PROJECT,capture_output=True,text=True)
        self.assertEqual(query.returncode,0,query.stderr)
        self.assertEqual(json.loads(query.stdout)["operation_ids"],["OP-1","OP-2"])
        with self.assertRaises(Exception):
            self.journal.run(self.request("OP-3",attempt=2,max_attempts=2,
                retry="OP-1",expected="OP-1",digest_value="b"*64),second_adapter,b"different")

    def test_payload_tool_version_and_internal_retry_mismatch_are_bounded(self):
        adapter=FakeAdapter(self.success_return())
        with self.assertRaisesRegex(OperationError,"request digest"):
            self.journal.run(self.request(digest_value="b"*64),adapter,b"different")
        self.assertEqual(adapter.calls,0)
        with self.assertRaisesRegex(OperationError,"tool version|Adapter identity"):
            self.journal.run(self.request(tool_version="9.9.9"),adapter,BODY)
        self.assertEqual(adapter.calls,0)
        with self.assertRaisesRegex(OperationError,"Adapter identity"):
            self.journal.run(self.request(provider_id="different-provider"),adapter,BODY)
        self.assertEqual(adapter.calls,0)
        over=OperationJournal(self.archive,self.rights)
        run=over.run(self.request("OP-OVER"),FakeAdapter(self.success_return(retries=2)),BODY)
        self.assertEqual(run.receipt.submission.version_id,"RESULT-OP-OVER")
        self.assertEqual(over.receipt("OP-OVER").status,OperationStatus.UNKNOWN)

    def test_provider_reconciliation_resolves_unknown_without_erasing_history(self):
        self.journal.run(self.request(),FakeAdapter(error=ToolAdapterError(
            "timeout",provider_request_id="PROVIDER-REQ-UNKNOWN")),BODY)
        self.assertEqual(self.journal.receipt("OP-1").status,OperationStatus.UNKNOWN)
        response=ToolResponse(status=OperationStatus.SUCCEEDED,provider_request_id="PROVIDER-REQ-UNKNOWN",
            result_sha256=hashlib.sha256(RESULT).hexdigest(),
            cost=CostObservation(kind=ObservationKind.ACTUAL,amount=Decimal("0.03"),currency="USD",
                basis="Provider reconciliation"),
            started_at=AT+timedelta(seconds=1),ended_at=AT+timedelta(seconds=2))
        self.journal.reconcile_unknown("OP-1",response,reconciliation_id="RECON-OP-1",
            evidence_version_ids=("EVIDENCE-1-v001",),recorded_at=AT+timedelta(minutes=3))
        current=self.journal.receipt("OP-1")
        self.assertEqual(current.status,OperationStatus.SUCCEEDED)
        self.assertEqual(current.source.value,"PROVIDER_RECONCILIATION")
        self.assertEqual(current.evidence_refs,("EVIDENCE-1-v001",))
        with self.assertRaisesRegex(OperationError,"Only an UNKNOWN operation"):
            self.journal.reconcile_unknown("OP-1",response,reconciliation_id="RECON-OP-2",
                evidence_version_ids=("EVIDENCE-1-v001",),recorded_at=AT+timedelta(minutes=4))


if __name__=="__main__":
    unittest.main()
