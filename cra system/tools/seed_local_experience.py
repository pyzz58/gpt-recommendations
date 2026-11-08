"""Seed the loopback-only synthetic CRA experience through the public API."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx2 as httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API = "http://127.0.0.1:18000"
FIXTURES = PROJECT_ROOT / "tests" / "fixtures"


def _expect(response: httpx.Response, expected: set[int] = {200}) -> Any:
    if response.status_code not in expected:
        raise RuntimeError(
            f"{response.request.method} {response.request.url.path} "
            f"returned {response.status_code}: {response.text[:1000]}"
        )
    return response.json()


class LocalSeed:
    def __init__(self, api_url: str):
        self.client = httpx.Client(base_url=api_url, timeout=60)
        _expect(
            self.client.post("/api/v1/auth/synthetic/session"),
            {200},
        )
        self.csrf = self.client.cookies.get("cra_csrf")
        if not self.csrf:
            raise RuntimeError("synthetic login did not issue a CSRF cookie")
        scopes = _expect(self.client.get("/api/v1/me/scopes"))
        study = next(
            item
            for item in scopes["studies"]
            if item["code"] == "SYNTH-001"
        )
        site = next(item for item in study["sites"] if item["code"] == "S01")
        self.study_id = study["id"]
        self.site_id = site["id"]

    def _headers(self, key: str | None = None) -> dict[str, str]:
        headers = {"X-CSRF-Token": self.csrf}
        if key:
            headers["Idempotency-Key"] = key
        return headers

    def upload_document(
        self,
        *,
        key: str,
        file: Path,
        title: str,
        document_type: str,
        purpose: str,
        media_type: str,
    ) -> dict[str, Any]:
        response = self.client.post(
            f"/api/v1/studies/{self.study_id}/documents",
            headers=self._headers(key),
            data={
                "title": title,
                "document_type": document_type,
                "purpose": purpose,
                "version_label": "v1",
                "expected_revision": "0",
                "site_id": self.site_id,
            },
            files={"file": (file.name, file.read_bytes(), media_type)},
        )
        return _expect(response, {202})

    def wait_parsed(self, version_id: str, timeout: float = 45) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            version = _expect(
                self.client.get(f"/api/v1/document-versions/{version_id}")
            )
            if version["parse_status"] in {
                "completed",
                "partial",
                "failed",
                "unsupported",
            }:
                return version
            time.sleep(0.5)
        raise TimeoutError(f"document version did not finish parsing: {version_id}")

    def ensure_subject(self) -> dict[str, Any]:
        response = self.client.post(
            f"/api/v1/studies/{self.study_id}/subjects",
            headers=self._headers(),
            json={
                "expected_revision": 0,
                "idempotency_key": "local-synthetic-subject-syn-edc-001",
                "site_id": self.site_id,
                "external_id": "SYN-EDC-001",
                "identity_namespace": "edc",
                "deidentified_label": "合成受试者 A",
            },
        )
        subject = _expect(response)
        self.subject_id = subject["id"]
        return subject

    def import_subject_facts(self) -> None:
        rows = [
            {
                "subject_external_id": "SYN-EDC-001",
                "fact_key": "treatment_due",
                "value_raw": "true",
                "value_type": "boolean",
                "observed_on": "2026-01-02",
                "precision": "date",
                "visit_key": "V1",
                "source_kind": "original_record",
                "source_ref": {
                    "source_type": "edc_row",
                    "source_id": "local-synthetic-context:1",
                    "locator": "synthetic_export!row=2",
                    "quote": "Pure synthetic local experience",
                },
            },
            {
                "subject_external_id": "SYN-EDC-001",
                "fact_key": "infusion_date",
                "value_raw": "2026-01-02",
                "value_type": "date",
                "observed_on": "2026-01-02",
                "precision": "date",
                "source_kind": "original_record",
                "source_ref": {
                    "source_type": "edc_row",
                    "source_id": "local-synthetic-context:2",
                    "locator": "synthetic_export!row=3",
                    "quote": "Pure synthetic local experience",
                },
            },
            {
                "subject_external_id": "SYN-EDC-001",
                "fact_key": "visit_date",
                "value_raw": "2026-01-02",
                "value_type": "date",
                "observed_on": "2026-01-02",
                "precision": "date",
                "visit_key": "V1",
                "source_kind": "original_record",
                "source_ref": {
                    "source_type": "edc_row",
                    "source_id": "local-synthetic-context:3",
                    "locator": "synthetic_export!row=4",
                    "quote": "Pure synthetic local experience",
                },
            },
            {
                "subject_external_id": "SYN-EDC-001",
                "fact_key": "lab_hemoglobin",
                "value_raw": "121",
                "value_type": "decimal",
                "observed_on": "2026-01-02",
                "precision": "unknown",
                "unit": "g/L",
                "source_kind": "original_record",
                "source_ref": {
                    "source_type": "edc_row",
                    "source_id": "local-synthetic-context:4",
                    "locator": "synthetic_export!row=5",
                    "quote": "Pure synthetic local experience",
                },
            },
        ]
        _expect(
            self.client.post(
                f"/api/v1/studies/{self.study_id}/facts/import",
                headers=self._headers(),
                json={
                    "expected_revision": 0,
                    "idempotency_key": "local-synthetic-context",
                    "site_id": self.site_id,
                    "identity_namespace": "edc",
                    "source_kind": "original_record",
                    "rows": rows,
                },
            )
        )

    def seed_carryover(self) -> None:
        upload = self.upload_document(
            key="local-synthetic-carryover-track",
            file=FIXTURES / "issues/artifacts/synthetic_carryover_track.xlsx",
            title="上次监查 synthetic Track",
            document_type="track",
            purpose="track",
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )
        self.wait_parsed(upload["document_version_id"])
        preview = _expect(
            self.client.post(
                f"/api/v1/document-versions/"
                f"{upload['document_version_id']}/carryover-imports/preview",
                headers=self._headers(),
                json={
                    "expected_revision": 0,
                    "idempotency_key": "local-synthetic-carryover-preview",
                    "site_id": self.site_id,
                },
            )
        )
        if preview["import_record"]["state"] != "confirmed":
            response = self.client.post(
                f"/api/v1/carryover-imports/{preview['import_record']['id']}/confirm",
                headers=self._headers(),
                json={
                    "expected_revision": preview["import_record"]["revision"],
                    "idempotency_key": "local-synthetic-carryover-confirm",
                    "corrections": [],
                },
            )
            if response.status_code != 409:
                _expect(response)
            current = _expect(
                self.client.get(
                    f"/api/v1/carryover-imports/"
                    f"{preview['import_record']['id']}"
                )
            )
            if current["import_record"]["state"] != "confirmed":
                raise RuntimeError(
                    "carryover import could not be confirmed idempotently"
                )

    def create_urgent_issue(self) -> None:
        _expect(
            self.client.post(
                f"/api/v1/studies/{self.study_id}/issues",
                headers=self._headers(),
                json={
                    "expected_revision": 0,
                    "idempotency_key": "local-synthetic-urgent-issue",
                    "site_id": self.site_id,
                    "issue_number": "LOCAL-URGENT",
                    "original_finding": (
                        "合成安全及数据更正事项，用于体验分项行动。"
                    ),
                    "location": "合成原始记录 row 14",
                    "known_progress": "上次监查后中心表示已开始处理。",
                    "source_kind": "manual",
                    "source_refs": [
                        {"locator": "synthetic_experience/issues.csv row 3"}
                    ],
                    "actions": [
                        {
                            "action_key": "PD",
                            "kind": "pd_reporting",
                            "requirement": "确认合成PD是否已上报。",
                        },
                        {
                            "action_key": "CORRECT",
                            "kind": "edc_correction",
                            "requirement": "核对并更正合成EDC值。",
                        },
                    ],
                },
            )
        )

    def seed_edc(self) -> dict[str, Any]:
        file = FIXTURES / "edc/artifacts/synthetic_edc_lab.xlsx"
        preview = self.client.post(
            f"/api/v1/studies/{self.study_id}/edc-imports/preview",
            headers=self._headers("local-synthetic-edc-preview"),
            data={
                "site_id": self.site_id,
                "title": "合成 EDC 检验导出",
                "export_started_at": "2026-01-03T08:00:00+00:00",
                "export_completed_at": "2026-01-03T08:05:00+00:00",
                "export_scope_json": json.dumps(
                    {
                        "status": "declared",
                        "forms": ["Hematology", "Chemistry"],
                        "subjects": ["SYN-EDC-001"],
                        "sites": ["S01"],
                        "date_start": "2026-01-01",
                        "date_end": "2026-01-03",
                        "filters": {},
                        "declared_complete": False,
                        "note": "Pure synthetic local experience export.",
                    }
                ),
                "included_sheets_json": json.dumps(
                    ["Hematology", "Chemistry"]
                ),
                "identity_namespace": "edc",
            },
            files={
                "file": (
                    file.name,
                    file.read_bytes(),
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet",
                )
            },
        )
        body = _expect(preview)
        columns = {
            "subject_external_id": "Subject ID",
            "visit_key": "Visit",
            "analyte": "Analyte",
            "value_raw": "Result",
            "unit": "Unit",
            "collected_on": "Collection Date",
            "collected_at": "Collection Time",
            "instance_type": "Instance",
            "repeat_instance": "Repeat No",
            "report_on": "Report Date",
            "specimen": "Specimen",
            "lower_limit": "LLN",
            "upper_limit": "ULN",
        }
        mapping = {
            "sheets": {
                sheet: {
                    "header_row": 1,
                    "data_start_row": 2,
                    "columns": columns,
                    "included": True,
                }
                for sheet in ("Hematology", "Chemistry")
            }
        }
        if body["state"] == "confirmed" and body.get("snapshot_id"):
            return _expect(
                self.client.get(
                    f"/api/v1/edc-snapshots/{body['snapshot_id']}"
                )
            )
        response = self.client.post(
            f"/api/v1/edc-imports/{body['id']}/confirm",
            headers=self._headers(),
            json={
                "expected_revision": body["revision"],
                "idempotency_key": "local-synthetic-edc-confirm",
                "mapping": mapping,
                "identity_namespace": "edc",
            },
        )
        if response.status_code == 409:
            current = _expect(
                self.client.get(f"/api/v1/edc-imports/{body['id']}")
            )
            if current.get("snapshot_id"):
                return _expect(
                    self.client.get(
                        f"/api/v1/edc-snapshots/{current['snapshot_id']}"
                    )
                )
        return _expect(response)

    def seed_lab_reports(self) -> dict[str, Any]:
        pdf = FIXTURES / "labs/artifacts/synthetic_lab_report.pdf"
        response = self.client.post(
            f"/api/v1/studies/{self.study_id}/lab-reports",
            headers=self._headers("local-synthetic-lab-report"),
            data={
                "site_id": self.site_id,
                "title": "合成文字PDF检验报告",
                "version_label": "v1",
            },
            files={"file": (pdf.name, pdf.read_bytes(), "application/pdf")},
        )
        report = _expect(response, {202})
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            report = _expect(
                self.client.get(f"/api/v1/lab-reports/{report['id']}")
            )
            if report["state"] != "pending":
                break
            time.sleep(0.5)
        png = FIXTURES / "labs/artifacts/synthetic_lab_report_eval.png"
        image_report = _expect(
            self.client.post(
                f"/api/v1/studies/{self.study_id}/lab-reports",
                headers=self._headers("local-synthetic-lab-image-ocr"),
                data={
                    "site_id": self.site_id,
                    "title": "合成清晰图像报告（Docling OCR）",
                    "version_label": "v1",
                },
                files={
                    "file": (png.name, png.read_bytes(), "image/png")
                },
            ),
            {202},
        )
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            image_report = _expect(
                self.client.get(
                    f"/api/v1/lab-reports/{image_report['id']}"
                )
            )
            if image_report["state"] != "pending":
                break
            time.sleep(0.5)
        return {"text_pdf": report, "image": image_report}

    def seed_templates(self) -> None:
        docs = [
            (
                "report",
                FIXTURES / "reports/artifacts/synthetic_monitoring_report.docx",
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document",
            ),
            (
                "track",
                FIXTURES / "reports/artifacts/synthetic_track_template.xlsx",
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet",
            ),
            (
                "letter",
                FIXTURES / "reports/artifacts/synthetic_visit_letter.docx",
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document",
            ),
        ]
        fields = {
            "study_code": "study_code",
            "site_code": "site_code",
            "site_name": "site_name",
            "visit_title": "visit_title",
            "generated_on": "generated_on",
            "visit_scope_note": "visit_scope_note",
            "coverage_summary": "coverage_summary",
            "not_checked_summary": "not_checked_summary",
            "next_steps_summary": "next_steps_summary",
            "user_summary": "user_summary",
            "user_conclusion": "user_conclusion",
        }
        for kind, file, media_type in docs:
            upload = self.upload_document(
                key=f"local-synthetic-{kind}-template",
                file=file,
                title=f"合成 {kind} 模板",
                document_type="template",
                purpose="template",
                media_type=media_type,
            )
            self.wait_parsed(upload["document_version_id"])
            if kind == "track":
                mapping = {
                    "output_kind": kind,
                    "output_format": "xlsx",
                    "xlsx": {
                        "cells": {},
                        "table": {
                            "sheet": "Track",
                            "start_row": 2,
                            "columns": {
                                "A": "issue_number",
                                "B": "section",
                                "C": "original_finding",
                                "D": "location",
                                "E": "recommendation",
                                "F": "status",
                                "G": "known_progress",
                                "H": "next_steps_text",
                                "I": "source_refs_text",
                            },
                        },
                        "required_variables": [],
                    },
                }
            else:
                mapping = {
                    "output_kind": kind,
                    "output_format": "docx",
                    "docx": {
                        "fields": fields,
                        "loops": (
                            {"letter_issues": "letter_issues"}
                            if kind == "letter"
                            else {
                                "prior_issues": "prior_issues",
                                "current_findings": "current_findings",
                            }
                        ),
                        "required_variables": (
                            ["study_code"]
                            if kind == "letter"
                            else [
                                "study_code",
                                "user_summary",
                                "user_conclusion",
                            ]
                        ),
                    },
                }
            _expect(
                self.client.post(
                    "/api/v1/template-versions",
                    headers=self._headers(f"local-synthetic-{kind}-mapping"),
                    json={
                        "expected_revision": 0,
                        "idempotency_key": f"local-synthetic-{kind}-mapping",
                        "source_document_version_id": upload[
                            "document_version_id"
                        ],
                        "title": f"合成 {kind} 模板映射",
                        "mapping": mapping,
                    },
                )
            )

    def seed_reference_documents(self) -> None:
        self.upload_document(
            key="local-synthetic-protocol",
            file=FIXTURES / "documents/artifacts/synthetic_rule_protocol.docx",
            title="合成方案（规则候选演练）",
            document_type="protocol",
            purpose="rule",
            media_type="application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document",
        )

    def seed_safety_rules(self) -> dict[str, Any]:
        rules_file = FIXTURES / "safety/rules.txt"
        upload = self.upload_document(
            key="local-synthetic-safety-rules",
            file=rules_file,
            title="合成方案/IB安全规则片段",
            document_type="protocol",
            purpose="rule",
            media_type="text/plain",
        )
        version = self.wait_parsed(upload["document_version_id"])
        if version["parse_status"] not in {"completed", "partial"}:
            raise RuntimeError("synthetic safety rules could not be parsed")
        extracted = _expect(
            self.client.post(
                f"/api/v1/document-versions/"
                f"{upload['document_version_id']}/rule-candidates",
                headers=self._headers(),
                json={
                    "expected_revision": 0,
                    "idempotency_key": "local-synthetic-safety-extract",
                },
            ),
            {200, 202},
        )
        rules = _expect(
            self.client.get(
                f"/api/v1/studies/{self.study_id}/rules",
                params={"site_id": self.site_id},
            )
        )
        if extracted["candidate_count"]:
            for rule in rules:
                current = rule["current_version"]
                if current is None or rule["rule_key"] not in {
                    "R-AE-COLLECTION-01",
                    "R-AE-GRADE-01",
                    "R-AE-SERIOUSNESS-01",
                    "R-AE-RELATEDNESS-01",
                    "R-AE-EXPECTEDNESS-01",
                    "R-AESI-01",
                    "R-DLT-01",
                    "R-PD-01",
                    "R-SAE-TIMELINESS-01",
                }:
                    continue
                response = self.client.post(
                    f"/api/v1/rules/{rule['id']}/confirmation",
                    headers=self._headers(),
                    json={
                        "expected_revision": rule["revision"],
                        "idempotency_key": (
                            f"local-synthetic-safety-confirm-"
                            f"{rule['rule_key']}"
                        ),
                        "base_version_id": current["id"],
                        "reason": "CRA confirms the synthetic safety rule subset",
                        "operations": [
                            {
                                "op": "edit_fields",
                                "summary": current["summary"],
                            }
                        ],
                    },
                )
                if response.status_code not in {200, 409}:
                    _expect(response)
        activation = self.client.post(
            "/api/v1/version-activations",
            headers=self._headers(),
            json={
                "expected_revision": 0,
                "idempotency_key": "local-synthetic-safety-activate",
                "document_version_id": upload["document_version_id"],
                "site_id": self.site_id,
                "starts_on": "2026-01-01",
                "reason": "Pure synthetic local safety rule activation",
            },
        )
        if activation.status_code not in {200, 409}:
            _expect(activation)
        return {
            "document_version_id": upload["document_version_id"],
            "rule_count": len(rules),
            "candidate_count": extracted["candidate_count"],
        }

    def seed_safety_assessment(self) -> dict[str, Any]:
        timeline = _expect(
            self.client.get(
                f"/api/v1/subjects/{self.subject_id}/timeline"
            )
        )
        event_fact = next(
            item for item in timeline if item["fact_key"] == "lab_hemoglobin"
        )
        return _expect(
            self.client.post(
                "/api/v1/safety-assessments",
                headers=self._headers(),
                json={
                    "expected_revision": 0,
                    "idempotency_key": "local-synthetic-safety-assessment",
                    "study_id": self.study_id,
                    "site_id": self.site_id,
                    "subject_id": self.subject_id,
                    "event_type": "laboratory_logic",
                    "event_date": "2026-01-02",
                    "event_fact_id": event_fact["id"],
                    "requested_dimensions": [
                        "grade",
                        "seriousness",
                        "reporting_timeliness",
                    ],
                    "note": (
                        "Pure synthetic local laboratory safety review. "
                        "Not a medical conclusion."
                    ),
                },
            )
        )
        self.upload_document(
            key="local-synthetic-rule-matrix",
            file=FIXTURES / "documents/artifacts/synthetic_rule_matrix_v2.docx",
            title="合成规则矩阵 v2（含例外）",
            document_type="protocol",
            purpose="rule",
            media_type="application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document",
        )

    def seed_review_template(self) -> dict[str, Any]:
        existing = _expect(
            self.client.get(
                "/api/v1/review-templates",
                params={
                    "study_id": self.study_id,
                    "site_id": self.site_id,
                },
            )
        )
        if existing:
            return existing[0]
        upload = self.upload_document(
            key="local-synthetic-review-template",
            file=(
                FIXTURES
                / "reviews/artifacts/synthetic_monitoring_review_v1.docx"
            ),
            title="合成中心监查报告核查模板 V1",
            document_type="template",
            purpose="template",
            media_type="application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document",
        )
        self.wait_parsed(upload["document_version_id"])
        preview = _expect(
            self.client.post(
                f"/api/v1/document-versions/"
                f"{upload['document_version_id']}/review-template-preview",
                headers=self._headers(),
            )
        )
        created = _expect(
            self.client.post(
                "/api/v1/review-templates",
                headers=self._headers(),
                json={
                    "expected_revision": 0,
                    "idempotency_key": (
                        "local-synthetic-review-template-config"
                    ),
                    "source_document_version_id": (
                        upload["document_version_id"]
                    ),
                    "title": "合成中心监查核查模板 V1",
                    "items": preview["questions"],
                    "warnings": preview["warnings"],
                },
            )
        )
        return created

    def summary(
        self,
        edc: dict[str, Any],
        labs: dict[str, Any],
        safety_rules: dict[str, Any],
        safety: dict[str, Any],
        review_template: dict[str, Any],
    ) -> dict[str, Any]:
        issues = _expect(
            self.client.get(
                f"/api/v1/studies/{self.study_id}/issues",
                params={"site_id": self.site_id},
            )
        )
        return {
            "source": "pure_synthetic",
            "study_id": self.study_id,
            "site_id": self.site_id,
            "subject_external_id": "SYN-EDC-001",
            "issue_numbers": sorted(item["issue_number"] for item in issues),
            "edc_snapshot_id": edc["id"],
            "text_pdf_report": {
                "id": labs["text_pdf"]["id"],
                "state": labs["text_pdf"]["state"],
                "provider": labs["text_pdf"]["provider_name"],
                "observations": labs["text_pdf"]["observations_count"],
            },
            "image_report_expectation": {
                "id": labs["image"]["id"],
                "state": labs["image"]["state"],
                "provider": labs["image"]["provider_name"],
                "observations": labs["image"]["observations_count"],
                "warning": labs["image"]["warnings"],
            },
            "safety_rules": safety_rules,
            "safety_assessment": {
                "id": safety["id"],
                "event_type": safety["event_type"],
                "status": safety["status"],
                "dimensions": [
                    item["dimension"] for item in safety["dimensions"]
                ],
                "questions": len(safety["questions"]),
                "provider_status": safety["provider_status"],
            },
            "review_template": {
                "id": review_template["id"],
                "title": review_template["title"],
                "item_count": len(review_template["items"]),
                "sections": len(
                    {
                        item["section_key"]
                        for item in review_template["items"]
                    }
                ),
            },
        }


def main() -> int:
    api_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_API
    seed = LocalSeed(api_url)
    seed.seed_reference_documents()
    seed.ensure_subject()
    seed.import_subject_facts()
    safety_rules = seed.seed_safety_rules()
    safety = seed.seed_safety_assessment()
    seed.seed_carryover()
    seed.create_urgent_issue()
    edc = seed.seed_edc()
    labs = seed.seed_lab_reports()
    seed.seed_templates()
    review_template = seed.seed_review_template()
    print(
        json.dumps(
            seed.summary(
                edc,
                labs,
                safety_rules,
                safety,
                review_template,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
