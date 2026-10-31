"""Generate deterministic synthetic W05 structured context fixtures."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from docx import Document
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "artifacts"
MANIFEST = ROOT / "manifest.json"


def _source_ref(row: str) -> dict[str, str]:
    return {
        "source_type": "edc_row",
        "source_id": f"synthetic-context:{row}",
        "locator": f"synthetic_export!row={row}",
        "quote": "Pure synthetic W05 context fixture",
    }


ROWS = [
    {
        "subject_external_id": "SYN-001",
        "fact_key": "study_phase",
        "value_raw": "treatment",
        "value_type": "string",
        "observed_on": "2021-01-01",
        "precision": "date",
        "repeat_instance": "_",
        "visit_key": "V1",
        "source_kind": "original_record",
        "source_ref": _source_ref("2"),
    },
    {
        "subject_external_id": "SYN-001",
        "fact_key": "treatment_due",
        "value_raw": "true",
        "value_type": "boolean",
        "observed_on": "2021-01-01",
        "precision": "date",
        "repeat_instance": "_",
        "visit_key": "V1",
        "source_kind": "original_record",
        "source_ref": _source_ref("2b"),
    },
    {
        "subject_external_id": "SYN-001",
        "fact_key": "infusion_date",
        "value_raw": "2021-01-01",
        "value_type": "date",
        "observed_on": "2021-01-01",
        "precision": "date",
        "repeat_instance": "_",
        "source_kind": "original_record",
        "source_ref": _source_ref("3"),
    },
    {
        "subject_external_id": "SYN-001",
        "fact_key": "visit_date",
        "value_raw": "2021-01-02",
        "value_type": "date",
        "observed_on": "2021-01-02",
        "precision": "date",
        "repeat_instance": "_",
        "visit_key": "V1",
        "source_kind": "original_record",
        "source_ref": _source_ref("4"),
    },
    {
        "subject_external_id": "SYN-001",
        "fact_key": "lab_hemoglobin",
        "value_raw": "121",
        "value_type": "decimal",
        "unit": "g/L",
        "observed_on": "2021-01-02",
        "precision": "unknown",
        "repeat_instance": "_",
        "source_kind": "original_record",
        "source_ref": _source_ref("5"),
    },
    {
        "subject_external_id": "SYN-002",
        "fact_key": "study_phase",
        "value_raw": "treatment",
        "value_type": "string",
        "observed_on": "2021-01-03",
        "precision": "date",
        "repeat_instance": "_",
        "visit_key": "V1",
        "source_kind": "original_record",
        "source_ref": _source_ref("6"),
    },
    {
        "subject_external_id": "SYN-002",
        "fact_key": "treatment_due",
        "value_raw": "true",
        "value_type": "boolean",
        "observed_on": "2021-01-03",
        "precision": "date",
        "repeat_instance": "_",
        "visit_key": "V1",
        "source_kind": "original_record",
        "source_ref": _source_ref("6b"),
    },
    {
        "subject_external_id": "SYN-002",
        "fact_key": "lab_hemoglobin",
        "value_raw": "118",
        "value_type": "decimal",
        "unit": "g/L",
        "observed_on": "2021-01-03",
        "precision": "unknown",
        "repeat_instance": "_",
        "source_kind": "original_record",
        "source_ref": _source_ref("7"),
    },
]


def _rule_docx(path: Path) -> None:
    document = Document()
    document.core_properties.title = "Synthetic W05 visit rule"
    document.core_properties.author = "Synthetic fixture generator"
    document.add_heading("Synthetic Subject Visit Rule", level=0)
    document.add_paragraph(
        "Rule R-INFUSION-01: Post-infusion visit must be checked against the "
        "documented infusion date."
    )
    document.add_paragraph("Trigger: present treatment_due")
    document.add_paragraph(
        "Branch V: WHEN visit_date within -2..2 days of infusion_date "
        "THEN record visit as within the synthetic window"
    )
    document.add_paragraph(
        "Branch L: WHEN visit_date within 3..14 days of infusion_date "
        "THEN create late-visit follow-up"
    )
    document.add_paragraph(
        "Exception X: WHEN protocol_waiver = true "
        "THEN preserve the approved synthetic waiver"
    )
    document.add_paragraph("Follow-up: explain the selected visit path")
    document.add_paragraph("Completion: actual date and rule version are visible")
    document.add_paragraph(
        "Required facts: treatment_due, infusion_date, visit_date"
    )
    document.save(path)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "synthetic_visit_rule.docx").unlink(missing_ok=True)
    _rule_docx(OUTPUT / "synthetic_visit_rule.docx")

    (OUTPUT / "synthetic_context.json").write_text(
        json.dumps({"rows": ROWS}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    csv_rows = [
        {
            **row,
            "source_ref": json.dumps(
                row["source_ref"], ensure_ascii=False, sort_keys=True
            ),
        }
        for row in ROWS
    ]
    csv_fields = sorted(
        {key for row in csv_rows for key in row}
    )
    with (OUTPUT / "synthetic_context.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=csv_fields, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(csv_rows)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Synthetic Context"
    headers = sorted({key for row in csv_rows for key in row})
    sheet.append(headers)
    for row in csv_rows:
        sheet.append([row.get(header, "") for header in headers])
    workbook.properties.creator = "Synthetic fixture generator"
    workbook.save(OUTPUT / "synthetic_context.xlsx")

    artifacts = []
    for path in sorted(OUTPUT.iterdir()):
        if not path.is_file():
            continue
        artifacts.append(
            {
                "artifact_id": (
                    path.stem.upper().replace("_", "-")
                    + "-"
                    + path.suffix.removeprefix(".").upper()
                ),
                "file": path.relative_to(ROOT).as_posix(),
                "source": "pure_synthetic",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    MANIFEST.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "group": "development_and_independent_expectations",
                "artifacts": artifacts,
                "expected_fact_keys": sorted(
                    {row["fact_key"] for row in ROWS}
                ),
                "expected_subjects": sorted(
                    {row["subject_external_id"] for row in ROWS}
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
