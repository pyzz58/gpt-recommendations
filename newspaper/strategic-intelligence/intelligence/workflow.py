"""W27 dependency-driven M01-M12 research workflow and checkpoint boundary."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
import hashlib
from typing import Literal, TypedDict, Self

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from pydantic import AwareDatetime, model_validator

from .archive import Archive, ArchiveError, Conflict, MissingVersion, canonical
from .contracts import (Contract, Digest, Identifier, NonBlank, ObjectKind, ReferenceUse,
                        Representation, RightsGrant, SourceTimes, StoredVersion,
                        VersionReference, VersionSubmission)
from .model_admission import (ModelAdmissionController, ModelDuty,
                              ModelUseAdmission)
from .operations import (OperationJournal, OperationRequest, OperationStatus)
from .research import ResearchRevision, ResearchRevisionController


class ResearchStep(str, Enum):
    M01 = "M01"
    M02 = "M02"
    M03 = "M03"
    M04 = "M04"
    M05 = "M05"
    M06 = "M06"
    M07 = "M07"
    M08 = "M08"
    M09 = "M09"
    M10 = "M10"
    M11 = "M11"
    M12 = "M12"


class StepOwner(str, Enum):
    JOINT = "JOINT"
    ADVISER = "ADVISER"
    TEACHER = "TEACHER"
    CONDITIONS = "CONDITIONS"


class StepDisposition(str, Enum):
    READY_FOR_NEXT = "READY_FOR_NEXT"
    CANDIDATE = "CANDIDATE"
    LIMITED = "LIMITED"
    REVISE = "REVISE"
    BLOCKED = "BLOCKED"


class Participant(str, Enum):
    B1 = "B1"
    B2 = "B2"


class ExecutionMethod(str, Enum):
    MANUAL = "MANUAL"
    ADMITTED_MODEL = "ADMITTED_MODEL"


class DossierCycleState(str, Enum):
    OPEN = "OPEN"
    LIMITED_CLOSURE = "LIMITED_CLOSURE"
    CLOSED_WITH_UNKNOWNS = "CLOSED_WITH_UNKNOWNS"


DEPENDENCIES = {
    ResearchStep.M01: (),
    ResearchStep.M02: (ResearchStep.M01,),
    ResearchStep.M03: (ResearchStep.M02,),
    ResearchStep.M04: (ResearchStep.M01, ResearchStep.M03),
    ResearchStep.M05: (ResearchStep.M03, ResearchStep.M04),
    ResearchStep.M06: (ResearchStep.M03, ResearchStep.M04),
    ResearchStep.M07: (
        ResearchStep.M02, ResearchStep.M04, ResearchStep.M05, ResearchStep.M06),
    ResearchStep.M08: (
        ResearchStep.M04, ResearchStep.M06, ResearchStep.M07),
    ResearchStep.M09: (ResearchStep.M07, ResearchStep.M08),
    ResearchStep.M10: (
        ResearchStep.M05, ResearchStep.M08, ResearchStep.M09),
    ResearchStep.M11: (
        ResearchStep.M02, ResearchStep.M07, ResearchStep.M08, ResearchStep.M09),
    ResearchStep.M12: (ResearchStep.M10, ResearchStep.M11),
}
STEP_ORDER = {step: index for index, step in enumerate(ResearchStep)}

OWNERS = {
    ResearchStep.M10: StepOwner.ADVISER,
    ResearchStep.M11: StepOwner.TEACHER,
    ResearchStep.M12: StepOwner.CONDITIONS,
}


class ParticipantQuestion(Contract):
    participant: Participant
    question: NonBlank
    rationale: NonBlank


class ResearchClosure(Contract):
    supported_scope: NonBlank
    remaining_unknowns: tuple[NonBlank, ...] = ()
    stop_reason: NonBlank
    next_trigger: NonBlank
    reopen_owner: Literal["T03", "T04", "T05", "T07", "T09"]


class MethodUseRecord(Contract):
    schema_version: Literal[1] = 1
    method_use_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    introduced_at: ResearchStep
    proposition: NonBlank
    source_version_ids: tuple[Identifier, ...]
    read_scope: NonBlank
    applicability_conditions: tuple[NonBlank, ...]
    expected_effect: NonBlank
    misuse_or_limit: NonBlank
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if not self.source_version_ids or len(self.source_version_ids) != len(
                set(self.source_version_ids)):
            raise ValueError("MethodUse needs unique actual source versions")
        if not self.applicability_conditions or len(
                self.applicability_conditions) != len(set(self.applicability_conditions)):
            raise ValueError("MethodUse needs unique applicability conditions")
        return self


class DossierStartRequest(Contract):
    schema_version: Literal[1] = 1
    dossier_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    revision_id: Identifier
    question_version_id: Identifier
    knowledge_cutoff: AwareDatetime
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.knowledge_cutoff > self.created_at:
            raise ValueError("Dossier cannot be created before its knowledge cutoff")
        return self


class StepBinding(Contract):
    step: ResearchStep
    record_version_id: Identifier
    disposition: StepDisposition


class DossierSnapshot(Contract):
    schema_version: Literal[1] = 1
    dossier_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    revision_id: Identifier
    question_version_id: Identifier
    knowledge_cutoff: AwareDatetime
    active_steps: tuple[StepBinding, ...]
    stale_steps: tuple[ResearchStep, ...]
    record_history_version_ids: tuple[Identifier, ...]
    method_use_version_ids: tuple[Identifier, ...]
    cycle_state: DossierCycleState
    graph_thread_id: Identifier
    previous_snapshot_version_id: Identifier | None
    content_review_required: Literal[True] = True
    publication_authorized: Literal[False] = False
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        steps = [item.step for item in self.active_steps]
        if len(steps) != len(set(steps)):
            raise ValueError("Dossier snapshot has duplicate active steps")
        for name, values in (
                ("stale step", self.stale_steps),
                ("record history", self.record_history_version_ids),
                ("method use", self.method_use_version_ids)):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate dossier {name}")
        if set(steps) & set(self.stale_steps):
            raise ValueError("A step cannot be active and stale at the same time")
        return self


class ResearchStepSubmission(Contract):
    schema_version: Literal[1] = 1
    step_record_id: Identifier
    previous_step_record_version_id: Identifier | None = None
    dossier_id: Identifier
    expected_snapshot_version_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    revision_id: Identifier
    step: ResearchStep
    owner: StepOwner
    disposition: StepDisposition
    artifact_version_ids: tuple[Identifier, ...]
    method_use_version_ids: tuple[Identifier, ...] = ()
    participant_questions: tuple[ParticipantQuestion, ...] = ()
    closure: ResearchClosure | None = None
    limitations: tuple[NonBlank, ...] = ()
    next_action: NonBlank | None = None
    execution_method: ExecutionMethod = ExecutionMethod.MANUAL
    model_admission_id: Identifier | None = None
    model_configuration_id: Identifier | None = None
    operation_request_version_id: Identifier | None = None
    model_domains: tuple[NonBlank, ...] = ()
    created_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if not self.artifact_version_ids or len(
                self.artifact_version_ids) != len(set(self.artifact_version_ids)):
            raise ValueError("A research step needs unique actual artifacts")
        for name, values in (
                ("method use", self.method_use_version_ids),
                ("participant participant", [item.participant for item in self.participant_questions]),
                ("limitation", self.limitations),
                ("model domain", self.model_domains)):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate step {name}")
        if self.owner is not OWNERS.get(self.step, StepOwner.JOINT):
            raise ValueError("Research step owner is invalid")
        if self.disposition in (
                StepDisposition.REVISE, StepDisposition.BLOCKED) and not self.next_action:
            raise ValueError("REVISE/BLOCKED step needs a concrete next action")
        if self.disposition is StepDisposition.LIMITED and not self.limitations:
            raise ValueError("LIMITED step must state its actual limitations")
        if self.step is ResearchStep.M12:
            if self.closure is None:
                raise ValueError("M12 needs an explicit limited closure")
        elif self.closure is not None:
            raise ValueError("Only M12 may carry a cycle closure")
        if self.execution_method is ExecutionMethod.ADMITTED_MODEL:
            if not all((
                    self.model_admission_id, self.model_configuration_id,
                    self.operation_request_version_id, self.model_domains)):
                raise ValueError("Admitted-model step needs admission, config, actual operation and domains")
        elif any((
                self.model_admission_id, self.model_configuration_id,
                self.operation_request_version_id)) or self.model_domains:
            raise ValueError("Manual step cannot carry model execution identity")
        return self


class ResearchStepRecord(Contract):
    schema_version: Literal[1] = 1
    step_record_id: Identifier
    step_record_version_id: Identifier
    previous_step_record_version_id: Identifier | None
    dossier_id: Identifier
    previous_snapshot_version_id: Identifier
    theme_id: Identifier
    spec_sha256: Digest
    revision_id: Identifier
    step: ResearchStep
    owner: StepOwner
    disposition: StepDisposition
    artifact_version_ids: tuple[Identifier, ...]
    method_use_version_ids: tuple[Identifier, ...]
    participant_questions: tuple[ParticipantQuestion, ...]
    closure: ResearchClosure | None
    limitations: tuple[NonBlank, ...]
    next_action: NonBlank | None
    execution_method: ExecutionMethod
    model_admission_id: Identifier | None
    model_configuration_id: Identifier | None
    operation_request_version_id: Identifier | None
    model_domains: tuple[NonBlank, ...]
    content_verified: Literal[False] = False
    workflow_ready_is_content_pass: Literal[False] = False
    publication_authorized: Literal[False] = False
    created_at: AwareDatetime


class WorkflowError(ArchiveError):
    """A M-step routing/version failure, never content completion."""


class _GraphState(TypedDict, total=False):
    target_step: str
    active_steps: tuple[tuple[str, str, str], ...]
    completed_steps: tuple[str, ...]
    last_step: str
    last_disposition: str
    blocked_reason: str


def _digest(value) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _version(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([prefix, identity]).encode()).hexdigest()[:32]


def _object(prefix: str, identity: str) -> str:
    return prefix + hashlib.sha256(
        canonical([identity]).encode()).hexdigest()[:32]


def _dependencies_satisfied(
        step: ResearchStep, active: dict[ResearchStep, StepBinding]) -> bool:
    for dependency in DEPENDENCIES[step]:
        binding = active.get(dependency)
        if binding is None:
            return False
        usable = {
            StepDisposition.READY_FOR_NEXT,
            StepDisposition.LIMITED,
        }
        if dependency is ResearchStep.M05 and step in (
                ResearchStep.M07, ResearchStep.M08):
            usable.add(StepDisposition.CANDIDATE)
        if binding.disposition not in usable:
            return False
    return True


def _descendants(step: ResearchStep) -> set[ResearchStep]:
    found = set()
    pending = [step]
    while pending:
        current = pending.pop()
        for candidate, dependencies in DEPENDENCIES.items():
            if current in dependencies and candidate not in found:
                found.add(candidate)
                pending.append(candidate)
    return found


class ResearchWorkflowController:
    def __init__(self, archive: Archive, rights: RightsGrant):
        if not isinstance(archive, Archive):
            raise TypeError("ResearchWorkflowController requires the shared Archive")
        if not isinstance(rights, RightsGrant):
            raise TypeError("ResearchWorkflowController requires an internal journal grant")
        self.archive = archive
        self.rights = rights
        self.research = ResearchRevisionController(archive, rights)
        self.model_admission = ModelAdmissionController(archive, rights)
        self.checkpointer = InMemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(_GraphState)
        steps = {step.value: step for step in ResearchStep}

        def route(state: _GraphState):
            target = state.get("target_step", "")
            if not target:
                return END
            if target not in steps:
                return "blocked"
            requested = steps[target]
            active_map = {
                ResearchStep(step): StepBinding(
                    step=ResearchStep(step), record_version_id=record_id,
                    disposition=StepDisposition(disposition))
                for step, record_id, disposition in state.get("active_steps", ())
            }
            if not _dependencies_satisfied(requested, active_map):
                return "blocked"
            return target

        def node(step_name: str):
            def apply(state: _GraphState):
                disposition = state.get("last_disposition", "")
                completed = state.get("completed_steps", ())
                if disposition in (
                        StepDisposition.READY_FOR_NEXT.value,
                        StepDisposition.LIMITED.value):
                    completed = tuple(sorted(set(completed) | {step_name}))
                return {
                    "target_step": "",
                    "last_step": step_name,
                    "completed_steps": completed,
                }
            return apply

        def blocked(state: _GraphState):
            return {
                "target_step": "",
                "blocked_reason": "Dependency-oriented graph rejected target step",
                "last_step": state.get("target_step", ""),
            }

        paths = {name: name for name in steps}
        paths["blocked"] = "blocked"
        paths[END] = END
        builder.add_conditional_edges(START, route, paths)
        for name in steps:
            builder.add_node(name, node(name))
            builder.add_edge(name, END)
        builder.add_node("blocked", blocked)
        builder.add_edge("blocked", END)
        return builder.compile(checkpointer=self.checkpointer)

    @staticmethod
    def _thread_config(thread_id: str):
        return {"configurable": {"thread_id": thread_id}}

    def _checkpoint(self, snapshot: DossierSnapshot,
                    target_step: ResearchStep | None = None,
                    disposition: StepDisposition | None = None) -> None:
        active = tuple(
            (binding.step.value, binding.record_version_id, binding.disposition.value)
            for binding in snapshot.active_steps)
        completed = tuple(sorted(
            binding.step.value for binding in snapshot.active_steps
            if binding.disposition in (
                StepDisposition.READY_FOR_NEXT, StepDisposition.LIMITED)))
        config = self._thread_config(snapshot.graph_thread_id)
        self.graph.invoke({
            "target_step": target_step.value if target_step else "",
            "active_steps": active,
            "completed_steps": completed,
            "last_disposition": disposition.value if disposition else "",
            "blocked_reason": "",
        }, config=config)

    def checkpoint_values(self, thread_id: str) -> dict:
        state = self.graph.get_state(self._thread_config(thread_id))
        return dict(state.values)

    def restore_checkpoint(self, snapshot_version_id: str) -> None:
        snapshot = self.load_snapshot(snapshot_version_id)
        self._checkpoint(snapshot)

    def start_dossier(self, request: DossierStartRequest) -> StoredVersion:
        if not isinstance(request, DossierStartRequest):
            raise TypeError("start_dossier requires DossierStartRequest")
        request = DossierStartRequest.model_validate_json(
            request.model_dump_json(warnings=False))
        revision = self.research.load_revision(request.revision_id)
        current = self.research.current_revision(request.theme_id)
        if current is None or current.revision_id != request.revision_id:
            raise WorkflowError("Dossier does not bind the current W16 research revision")
        if (revision.theme_id != request.theme_id
                or revision.spec_sha256 != request.spec_sha256):
            raise WorkflowError("Dossier revision theme/specification differs")
        if (revision.question_version_id is not None
                and revision.question_version_id != request.question_version_id):
            raise WorkflowError("Dossier question differs from the research revision")
        if request.created_at < revision.created_at:
            raise WorkflowError("Dossier predates its research revision")
        question = self.archive.get(request.question_version_id)
        if question.submission.kind is not ObjectKind.QUESTION_VERSION:
            raise WorkflowError("Dossier question dependency is not a QuestionVersion")
        snapshot = DossierSnapshot(
            dossier_id=request.dossier_id, theme_id=request.theme_id,
            spec_sha256=request.spec_sha256, revision_id=request.revision_id,
            question_version_id=request.question_version_id,
            knowledge_cutoff=request.knowledge_cutoff,
            active_steps=(), stale_steps=(),
            record_history_version_ids=(), method_use_version_ids=(),
            cycle_state=DossierCycleState.OPEN,
            graph_thread_id="THREAD-" + _digest([request.dossier_id])[:32],
            previous_snapshot_version_id=None,
            created_at=request.created_at)
        stored = self._store_snapshot(
            snapshot, question_version_id=request.question_version_id,
            revision_version_id=request.revision_id,
            previous_snapshot=None, created_at=request.created_at)
        self._checkpoint(snapshot)
        return stored

    def append_method(self, method: MethodUseRecord) -> StoredVersion:
        if not isinstance(method, MethodUseRecord):
            raise TypeError("append_method requires MethodUseRecord")
        method = MethodUseRecord.model_validate_json(
            method.model_dump_json(warnings=False))
        sources = []
        for source_version_id in method.source_version_ids:
            stored = self.archive.get(source_version_id)
            if stored.body_retention_revoked:
                raise WorkflowError("Method source was withdrawn")
            if stored.submission.spec_sha256 != method.spec_sha256:
                raise WorkflowError("Method source uses a different specification")
            sources.append(stored)
        version_id = _version("METHOD-USE-", method.method_use_id)
        object_id = _object("METHOD-USE-OBJECT-", method.method_use_id)
        references = tuple(
            VersionReference(target_version_id=source_id,
                use=ReferenceUse.SOURCE, locator=f"method source {index}")
            for index, source_id in enumerate(method.source_version_ids))
        expected = {object_id: None}
        expected.update({
            stored.submission.object_id: stored.submission.version_id for stored in sources})
        submission = VersionSubmission(
            schema_version=2, object_id=object_id, version_id=version_id,
            kind=ObjectKind.METHOD_USE,
            title=f"method use {method.method_use_id}",
            spec_sha256=method.spec_sha256, created_at=method.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY, references=references)
        return self.archive.append(
            submission, canonical(method.model_dump(mode="json")).encode(),
            expected_current=expected)

    def load_method(self, method_version_id: str) -> MethodUseRecord:
        stored = self.archive.get(method_version_id)
        if stored.submission.kind is not ObjectKind.METHOD_USE:
            raise WorkflowError("Requested version is not a MethodUse")
        method = MethodUseRecord.model_validate_json(
            self.archive.read_body(method_version_id))
        if stored.submission.version_id != _version(
                "METHOD-USE-", method.method_use_id):
            raise WorkflowError("MethodUse identity mismatch")
        return method

    def current_snapshot(self, dossier_id: str) -> tuple[StoredVersion, DossierSnapshot]:
        stored = self.archive.latest(_object("DOSSIER-OBJECT-", dossier_id))
        if stored is None:
            raise WorkflowError("Dossier does not exist")
        return stored, self.load_snapshot(stored.submission.version_id)

    @staticmethod
    def _snapshot_version_id(snapshot: DossierSnapshot) -> str:
        return _version("DOSSIER-SNAPSHOT-", canonical([
            snapshot.dossier_id,
            snapshot.previous_snapshot_version_id,
            snapshot.record_history_version_ids,
            [item.model_dump(mode="json") for item in snapshot.active_steps],
            [item.value for item in snapshot.stale_steps],
        ]))

    def _store_snapshot(self, snapshot: DossierSnapshot, *,
                        question_version_id: str, revision_version_id: str,
                        previous_snapshot: StoredVersion | None,
                        created_at: datetime) -> StoredVersion:
        object_id = _object("DOSSIER-OBJECT-", snapshot.dossier_id)
        version_id = self._snapshot_version_id(snapshot)
        question_stored = self.archive.get(question_version_id)
        expected = {
            object_id: previous_snapshot.submission.version_id if previous_snapshot else None,
            question_stored.submission.object_id: question_version_id,
            self.research._revision_object(snapshot.theme_id): revision_version_id,
        }
        references = [
            VersionReference(target_version_id=revision_version_id,
                use=ReferenceUse.BASIS, locator="exact research revision"),
            VersionReference(target_version_id=question_version_id,
                use=ReferenceUse.BASIS, locator="exact research question"),
            *(
                VersionReference(target_version_id=record_id,
                    use=ReferenceUse.SUPPORT, locator=f"active step record {index}")
                for index, record_id in enumerate(snapshot.record_history_version_ids)
            ),
        ]
        submission = VersionSubmission(
            schema_version=2, object_id=object_id, version_id=version_id,
            parent_version_id=previous_snapshot.submission.version_id if previous_snapshot else None,
            kind=ObjectKind.DOSSIER, title=f"research dossier {snapshot.dossier_id}",
            spec_sha256=snapshot.spec_sha256, created_at=created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY, references=tuple(references))
        return self.archive.append(
            submission, canonical(snapshot.model_dump(mode="json")).encode(),
            expected_current=expected)

    def load_snapshot(self, snapshot_version_id: str) -> DossierSnapshot:
        stored = self.archive.get(snapshot_version_id)
        if stored.submission.kind is not ObjectKind.DOSSIER:
            raise WorkflowError("Requested version is not a ResearchDossier snapshot")
        snapshot = DossierSnapshot.model_validate_json(
            self.archive.read_body(snapshot_version_id))
        if (stored.submission.version_id != self._snapshot_version_id(snapshot)
                or stored.submission.object_id != _object(
                    "DOSSIER-OBJECT-", snapshot.dossier_id)
                or stored.submission.parent_version_id
                != snapshot.previous_snapshot_version_id
                or stored.submission.spec_sha256 != snapshot.spec_sha256
                or stored.submission.created_at != snapshot.created_at):
            raise WorkflowError("Research dossier snapshot identity mismatch")
        return snapshot

    def _validate_model_execution(self, submission: ResearchStepSubmission) -> None:
        if submission.execution_method is ExecutionMethod.MANUAL:
            return
        duty = {
            StepOwner.ADVISER: ModelDuty.ADVISER,
            StepOwner.TEACHER: ModelDuty.TEACHER,
        }.get(submission.owner, ModelDuty.FACT_EXTRACTION)
        if not self.model_admission.authorizes(
                submission.model_admission_id,
                configuration_id=submission.model_configuration_id,
                duty=duty, domains=submission.model_domains,
                require_given_material=True, at=submission.created_at):
            raise WorkflowError("Model execution is outside a current admitted task scope")
        operation = self.archive.get(submission.operation_request_version_id)
        if operation.submission.kind is not ObjectKind.OPERATION_REQUEST:
            raise WorkflowError("Model execution has no actual OperationRequest")
        operation_body = OperationRequest.model_validate_json(
            self.archive.read_body(submission.operation_request_version_id))
        configuration = self.model_admission.load_configuration(
            submission.model_configuration_id)
        if (operation_body.spec_sha256 != submission.spec_sha256
                or operation_body.configuration_sha256
                != configuration.configuration_sha256):
            raise WorkflowError("Model operation and task configuration differ")
        receipt = OperationJournal(self.archive, self.rights).receipt(
            submission.operation_request_version_id)
        if receipt is None or receipt.status is not OperationStatus.SUCCEEDED:
            raise WorkflowError("Model step has no successful actual operation receipt")
        for artifact_id in submission.artifact_version_ids:
            artifact = self.archive.get(artifact_id)
            if not any(reference.target_version_id
                       == submission.operation_request_version_id
                       for reference in artifact.submission.references):
                raise WorkflowError(
                    "Admitted-model artifact does not reference its actual operation")

    def submit_step(self, submission: ResearchStepSubmission) -> StoredVersion:
        if not isinstance(submission, ResearchStepSubmission):
            raise TypeError("submit_step requires ResearchStepSubmission")
        submission = ResearchStepSubmission.model_validate_json(
            submission.model_dump_json(warnings=False))
        previous_snapshot, snapshot = self.current_snapshot(submission.dossier_id)
        if previous_snapshot.submission.version_id != submission.expected_snapshot_version_id:
            raise Conflict("Research dossier changed after this step was prepared")
        if (snapshot.theme_id != submission.theme_id
                or snapshot.spec_sha256 != submission.spec_sha256
                or snapshot.revision_id != submission.revision_id):
            raise WorkflowError("Step and dossier theme/revision/specification differ")
        revision = self.research.load_revision(snapshot.revision_id)
        current_revision = self.research.current_revision(snapshot.theme_id)
        if (current_revision is None
                or current_revision.revision_id != revision.revision_id):
            raise WorkflowError("Dossier research revision is stale")
        active = {binding.step: binding for binding in snapshot.active_steps}
        if not _dependencies_satisfied(submission.step, active):
            raise WorkflowError("Research step dependencies are not ready")
        if submission.step is ResearchStep.M02:
            participants = {item.participant for item in submission.participant_questions}
            if participants != {Participant.B1, Participant.B2}:
                raise WorkflowError("M02 needs early B1 and B2 questions")
        if submission.step is ResearchStep.M07:
            methods = [self.load_method(method_id)
                       for method_id in submission.method_use_version_ids]
            if not methods:
                raise WorkflowError("M07 must consolidate at least one MethodUse")
            if not any(method.introduced_at is not ResearchStep.M07 for method in methods):
                raise WorkflowError("M07 cannot be the first point where method is selected")
            if not set(snapshot.method_use_version_ids) <= set(
                    submission.method_use_version_ids):
                raise WorkflowError("M07 must consolidate every earlier MethodUse")
        methods = []
        for method_id in submission.method_use_version_ids:
            method = self.load_method(method_id)
            if (method.theme_id != submission.theme_id
                    or method.spec_sha256 != submission.spec_sha256):
                raise WorkflowError("MethodUse crosses the dossier theme/specification")
            if STEP_ORDER[method.introduced_at] > STEP_ORDER[submission.step]:
                raise WorkflowError("Step cannot use a method introduced later")
            methods.append(method)
        if submission.created_at < previous_snapshot.submission.created_at:
            raise WorkflowError("Step predates the dossier snapshot")
        artifacts = []
        for artifact_id in submission.artifact_version_ids:
            stored = self.archive.get(artifact_id)
            if stored.body_retention_revoked:
                raise WorkflowError("Step artifact was withdrawn")
            if stored.submission.spec_sha256 != submission.spec_sha256:
                raise WorkflowError("Step artifact uses another specification")
            if not any(reference.target_version_id == submission.revision_id
                       for reference in stored.submission.references):
                raise WorkflowError("Step artifact does not reference the exact research revision")
            artifacts.append(stored)
        self._validate_model_execution(submission)
        step_object = _object(
            "RESEARCH-STEP-OBJECT-", canonical([
                submission.dossier_id, submission.step.value]))
        latest_step = self.archive.latest(step_object)
        if submission.previous_step_record_version_id is None:
            if latest_step is not None:
                raise WorkflowError("Existing step history requires previous record")
        elif latest_step is None or latest_step.submission.version_id != submission.previous_step_record_version_id:
            raise WorkflowError("Previous M-step record is not current")
        version_id = _version("RESEARCH-STEP-", canonical([
            submission.step_record_id, submission.expected_snapshot_version_id,
            submission.previous_step_record_version_id]))
        record = ResearchStepRecord(
            step_record_id=submission.step_record_id,
            step_record_version_id=version_id,
            previous_step_record_version_id=submission.previous_step_record_version_id,
            dossier_id=submission.dossier_id,
            previous_snapshot_version_id=submission.expected_snapshot_version_id,
            theme_id=submission.theme_id, spec_sha256=submission.spec_sha256,
            revision_id=submission.revision_id, step=submission.step,
            owner=submission.owner, disposition=submission.disposition,
            artifact_version_ids=submission.artifact_version_ids,
            method_use_version_ids=submission.method_use_version_ids,
            participant_questions=submission.participant_questions,
            closure=submission.closure, limitations=submission.limitations,
            next_action=submission.next_action,
            execution_method=submission.execution_method,
            model_admission_id=submission.model_admission_id,
            model_configuration_id=submission.model_configuration_id,
            operation_request_version_id=submission.operation_request_version_id,
            model_domains=submission.model_domains,
            created_at=submission.created_at)
        step_references = [
            VersionReference(target_version_id=submission.expected_snapshot_version_id,
                use=ReferenceUse.BASIS, locator="prior dossier snapshot"),
            VersionReference(target_version_id=submission.revision_id,
                use=ReferenceUse.BASIS, locator="exact research revision"),
            *(
                VersionReference(target_version_id=artifact_id,
                    use=ReferenceUse.SUPPORT, locator=f"step artifact {index}")
                for index, artifact_id in enumerate(submission.artifact_version_ids)
            ),
            *(
                VersionReference(target_version_id=method_id,
                    use=ReferenceUse.SUPPORT, locator=f"method use {index}")
                for index, method_id in enumerate(submission.method_use_version_ids)
            ),
        ]
        step_expected = {
            step_object: latest_step.submission.version_id if latest_step else None,
            previous_snapshot.submission.object_id: previous_snapshot.submission.version_id,
            self.research._revision_object(snapshot.theme_id): snapshot.revision_id,
        }
        for stored in (*artifacts, *(
                self.archive.get(method_id)
                for method_id in submission.method_use_version_ids)):
            step_expected[stored.submission.object_id] = stored.submission.version_id
        step_submission = VersionSubmission(
            schema_version=2, object_id=step_object, version_id=version_id,
            parent_version_id=submission.previous_step_record_version_id,
            kind=ObjectKind.RESEARCH_STEP_RECORD,
            title=f"{submission.dossier_id} {submission.step.value}",
            spec_sha256=submission.spec_sha256, created_at=submission.created_at,
            source_times=SourceTimes(), rights=self.rights,
            representation=Representation.FULL_BODY,
            references=tuple(step_references))
        step_stored = self.archive.append(
            step_submission, canonical(record.model_dump(mode="json")).encode(),
            expected_current=step_expected)
        updated_active = dict(active)
        invalidated = _descendants(submission.step)
        for downstream in invalidated:
            updated_active.pop(downstream, None)
        updated_active[submission.step] = StepBinding(
            step=submission.step, record_version_id=step_stored.submission.version_id,
            disposition=submission.disposition)
        cycle_state = (
            DossierCycleState.OPEN
            if invalidated or submission.step is not ResearchStep.M12
            else snapshot.cycle_state)
        if submission.step is ResearchStep.M12 and submission.disposition in (
                StepDisposition.READY_FOR_NEXT, StepDisposition.LIMITED):
            cycle_state = (
                DossierCycleState.LIMITED_CLOSURE
                if submission.closure and submission.closure.remaining_unknowns
                else DossierCycleState.CLOSED_WITH_UNKNOWNS)
        stale = tuple(sorted(
            (set(snapshot.stale_steps) | invalidated) - {submission.step},
            key=lambda item: item.value))
        history = tuple(sorted(
            set(snapshot.record_history_version_ids) | {
                step_stored.submission.version_id}))
        method_ids = tuple(sorted(
            set(snapshot.method_use_version_ids)
            | set(submission.method_use_version_ids)))
        next_snapshot = DossierSnapshot(
            dossier_id=snapshot.dossier_id, theme_id=snapshot.theme_id,
            spec_sha256=snapshot.spec_sha256, revision_id=snapshot.revision_id,
            question_version_id=snapshot.question_version_id,
            knowledge_cutoff=snapshot.knowledge_cutoff,
            active_steps=tuple(sorted(
                updated_active.values(), key=lambda item: item.step.value)),
            stale_steps=stale, record_history_version_ids=history,
            method_use_version_ids=method_ids, cycle_state=cycle_state,
            graph_thread_id=snapshot.graph_thread_id,
            previous_snapshot_version_id=previous_snapshot.submission.version_id,
            created_at=submission.created_at)
        snapshot_stored = self._store_snapshot(
            next_snapshot, question_version_id=snapshot.question_version_id,
            revision_version_id=snapshot.revision_id,
            previous_snapshot=previous_snapshot,
            created_at=submission.created_at)
        self._checkpoint(
            next_snapshot, submission.step, submission.disposition)
        return snapshot_stored

    def load_step_record(self, step_record_version_id: str) -> ResearchStepRecord:
        stored = self.archive.get(step_record_version_id)
        if stored.submission.kind is not ObjectKind.RESEARCH_STEP_RECORD:
            raise WorkflowError("Requested version is not a ResearchStepRecord")
        record = ResearchStepRecord.model_validate_json(
            self.archive.read_body(step_record_version_id))
        if (record.step_record_version_id != step_record_version_id
                or stored.submission.object_id != _object(
                    "RESEARCH-STEP-OBJECT-",
                    canonical([record.dossier_id, record.step.value]))
                or stored.submission.spec_sha256 != record.spec_sha256
                or stored.submission.created_at != record.created_at):
            raise WorkflowError("Research step record identity mismatch")
        return record
