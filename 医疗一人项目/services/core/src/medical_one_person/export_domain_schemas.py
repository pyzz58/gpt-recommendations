from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from medical_one_person.domain.audits import AuditEvaluationFixture, AuditFindingSpec
from medical_one_person.domain.datasets import CleaningSpec, StatisticalPlanSpec
from medical_one_person.domain.exports import ExportTemplateCatalog, StructuredReport
from medical_one_person.domain.external import (
    ContactSpec,
    ContractSpec,
    DeliverableSpec,
    EngagementSpec,
    ExpertSpec,
    ExternalAuthorizationSpec,
    OrganizationSpec,
    ProfessionalRecordSpec,
    QuoteSpec,
)
from medical_one_person.domain.mail import MailDraftSpec, MailSendAuthorizationSpec
from medical_one_person.domain.opportunities import (
    CostEstimate,
    OpportunityCard,
    ProbabilityEstimate,
    ScientificBrief,
)
from medical_one_person.domain.recovery import (
    BackupCreateRequest,
    BackupView,
    RestoreCheckRequest,
    RestoreCheckView,
    TrashDocumentRequest,
)
from medical_one_person.domain.workflows import (
    CriterionResult,
    WorkflowDefinition,
)


def main() -> None:
    project_root = Path(__file__).resolve().parents[4]
    schemas = project_root / "schemas"
    schemas.mkdir(parents=True, exist_ok=True)
    targets: dict[str, tuple[type[BaseModel], str, str]] = {
        "opportunity-card.v1.schema.json": (
            OpportunityCard,
            "urn:medical-one-person:opportunity-card:v1",
            "Opportunity comparison contract from TR-11; validation does not "
            "establish scientific validity.",
        ),
        "scientific-brief.v1.schema.json": (
            ScientificBrief,
            "urn:medical-one-person:scientific-brief:v1",
            "Scientific brief contract from TR-11; synthetic examples are not evidence.",
        ),
        "probability-estimate.v1.schema.json": (
            ProbabilityEstimate,
            "urn:medical-one-person:probability-estimate:v1",
            "Event-specific probability contract; unknown evidence must remain unknown.",
        ),
        "cost-estimate.v1.schema.json": (
            CostEstimate,
            "urn:medical-one-person:cost-estimate:v1",
            "Stage-specific cost contract; unknown costs cannot be represented as zero.",
        ),
        "workflow-definition.v1.schema.json": (
            WorkflowDefinition,
            "urn:medical-one-person:workflow-definition:v1",
            "Strict three-domain workflow contract; config validity does not prove "
            "scientific or regulatory applicability.",
        ),
        "criterion-result.v1.schema.json": (
            CriterionResult,
            "urn:medical-one-person:criterion-result:v1",
            "Structured stage-criterion record; object references do not prove "
            "scientific validity.",
        ),
        "dataset-cleaning.v1.schema.json": (
            CleaningSpec,
            "urn:medical-one-person:dataset-cleaning:v1",
            "Versioned table cleaning contract; derivation does not overwrite raw data.",
        ),
        "statistical-plan.v1.schema.json": (
            StatisticalPlanSpec,
            "urn:medical-one-person:statistical-plan:v1",
            "Pre-specified deterministic statistical plan contract.",
        ),
        "structured-report.v1.schema.json": (
            StructuredReport,
            "urn:medical-one-person:structured-report:v1",
            "Version-bound report content rendered into Office and PDF files.",
        ),
        "export-template-catalog.v1.schema.json": (
            ExportTemplateCatalog,
            "urn:medical-one-person:export-template-catalog:v1",
            "Fixed-version export template catalog contract.",
        ),
        "mail-draft.v1.schema.json": (
            MailDraftSpec,
            "urn:medical-one-person:mail-draft:v1",
            "Mail draft contract; saving a draft does not authorize sending.",
        ),
        "mail-send-authorization.v1.schema.json": (
            MailSendAuthorizationSpec,
            "urn:medical-one-person:mail-send-authorization:v1",
            "Time- and count-bounded local send authorization contract.",
        ),
        "external-organization.v1.schema.json": (
            OrganizationSpec,
            "urn:medical-one-person:external-organization:v1",
            "External provider candidate/verification contract.",
        ),
        "external-contact.v1.schema.json": (
            ContactSpec,
            "urn:medical-one-person:external-contact:v1",
            "External contact provenance and verification contract.",
        ),
        "external-expert.v1.schema.json": (
            ExpertSpec,
            "urn:medical-one-person:external-expert:v1",
            "Expert candidate and engagement-state contract.",
        ),
        "external-engagement.v1.schema.json": (
            EngagementSpec,
            "urn:medical-one-person:external-engagement:v1",
            "External work package scope contract.",
        ),
        "external-quote.v1.schema.json": (
            QuoteSpec,
            "urn:medical-one-person:external-quote:v1",
            "Received quote and original-document contract.",
        ),
        "external-contract.v1.schema.json": (
            ContractSpec,
            "urn:medical-one-person:external-contract:v1",
            "Contract draft contract; drafting does not imply signature.",
        ),
        "external-deliverable.v1.schema.json": (
            DeliverableSpec,
            "urn:medical-one-person:external-deliverable:v1",
            "Expected external deliverable and raw-data contract.",
        ),
        "professional-record.v1.schema.json": (
            ProfessionalRecordSpec,
            "urn:medical-one-person:professional-record:v1",
            "Regulatory, patent, financial and commercial fact contract "
            "with source/date boundaries.",
        ),
        "external-authorization.v1.schema.json": (
            ExternalAuthorizationSpec,
            "urn:medical-one-person:external-authorization:v1",
            "Time- and amount-bounded local external action authorization contract.",
        ),
        "audit-finding.v1.schema.json": (
            AuditFindingSpec,
            "urn:medical-one-person:audit-finding:v1",
            "Structured A25/A26 review finding; a rule hit is not proof of "
            "scientific correctness.",
        ),
        "audit-evaluation-fixture.v1.schema.json": (
            AuditEvaluationFixture,
            "urn:medical-one-person:audit-evaluation-fixture:v1",
            "Synthetic deterministic audit regression fixture; passing cases does "
            "not certify medical or scientific capability.",
        ),
        "knowledge-trash.v1.schema.json": (
            TrashDocumentRequest,
            "urn:medical-one-person:knowledge-trash:v1",
            "Explicit logical-delete request; the original remains recoverable.",
        ),
        "backup-create-request.v1.schema.json": (
            BackupCreateRequest,
            "urn:medical-one-person:backup-create-request:v1",
            "Project backup request. The passphrase is transient and is not persisted.",
        ),
        "backup-snapshot.v1.schema.json": (
            BackupView,
            "urn:medical-one-person:backup-snapshot:v1",
            "Backup metadata and manifest without a stored encryption key.",
        ),
        "restore-check-request.v1.schema.json": (
            RestoreCheckRequest,
            "urn:medical-one-person:restore-check-request:v1",
            "Transient passphrase request for isolated restore verification.",
        ),
        "restore-check.v1.schema.json": (
            RestoreCheckView,
            "urn:medical-one-person:restore-check:v1",
            "Isolated restore verification result; the active database is not overwritten.",
        ),
    }
    for name, (model, schema_id, description) in targets.items():
        content = model.model_json_schema()
        content = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": schema_id,
            **content,
            "description": description,
        }
        target = schemas / name
        target.write_text(
            json.dumps(content, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(target)


if __name__ == "__main__":
    main()
