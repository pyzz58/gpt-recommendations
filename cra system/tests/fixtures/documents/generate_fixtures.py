"""Generate the public, synthetic W03 source corpus deterministically enough.

The generated files are committed. Tests never download clinical material or
call a provider while creating fixtures.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from docx import Document
from openpyxl import Workbook
from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "artifacts"
MANIFEST_PATH = ROOT.parent / "manifest.json"


def _synthetic_docx(path: Path) -> None:
    document = Document()
    document.core_properties.title = "Synthetic protocol excerpt"
    document.core_properties.author = "Synthetic fixture generator"
    document.core_properties.created = datetime(2026, 10, 31)
    document.core_properties.modified = datetime(2026, 10, 31)
    document.add_heading("Synthetic Study Protocol", level=0)
    document.add_heading("1. Screening", level=1)
    paragraph = document.add_paragraph()
    paragraph.add_run("Consent must be obtained before ")
    paragraph.add_run("any study procedure").bold = True
    paragraph.add_run(" begins. This sentence is synthetic.")
    document.add_heading("2. Laboratory", level=1)
    run = document.add_paragraph().add_run(
        "If local laboratory reference ranges are used, verify the applicable "
        "project rule. "
    )
    run.italic = True
    table = document.add_table(rows=3, cols=3)
    table.style = "Table Grid"
    table.cell(0, 0).text = "Visit"
    table.cell(0, 1).text = "Window"
    table.cell(0, 2).text = "Condition"
    table.cell(0, 0).merge(table.cell(0, 1))
    table.cell(1, 0).text = "V1"
    table.cell(1, 1).text = "±3 days"
    table.cell(1, 2).text = "Synthetic condition C -> path B"
    table.cell(2, 0).text = "V2"
    table.cell(2, 1).text = "±5 days"
    table.cell(2, 2).text = "Synthetic condition D -> path F"
    media = Image.new("RGB", (24, 12), "white")
    media_bytes = BytesIO()
    media.save(media_bytes, format="PNG")
    media_bytes.seek(0)
    document.add_picture(media_bytes)
    document.add_heading("3. Background", level=1)
    document.add_paragraph(
        "This is explicitly marked background content and is not a requirement."
    )
    document.add_paragraph("Synthetic footnote target.")
    document.save(path)

    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        with zipfile.ZipFile(path) as source:
            source.extractall(temp)
        document_xml = temp / "word/document.xml"
        xml = document_xml.read_text(encoding="utf-8")
        target = (
            "<w:p><w:r><w:t>This is explicitly marked background content "
            "and is not a requirement.</w:t></w:r></w:p>"
        )
        if target not in xml:
            raise RuntimeError("background fixture paragraph not found")
        wrapped = (
            '<w:sdt><w:sdtPr><w:tag w:val="CRA-BACKGROUND"/>'
            "<w:alias w:val=\"Background\"/></w:sdtPr><w:sdtContent>"
            + target
            + "</w:sdtContent></w:sdt>"
        )
        xml = xml.replace(target, wrapped, 1)
        footnote_target = (
            "<w:p><w:r><w:t>Synthetic footnote target.</w:t></w:r></w:p>"
        )
        if footnote_target not in xml:
            raise RuntimeError("footnote fixture paragraph not found")
        xml = xml.replace(
            footnote_target,
            (
                "<w:p><w:r><w:t>Synthetic footnote target.</w:t></w:r>"
                '<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr>'
                '<w:footnoteReference w:id="1"/></w:r></w:p>'
            ),
            1,
        )
        document_xml.write_text(xml, encoding="utf-8")
        (temp / "word/footnotes.xml").write_text(
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>
  <w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>
  <w:footnote w:id="1"><w:p><w:r><w:t>Synthetic footnote: applicability is illustrative only.</w:t></w:r></w:p></w:footnote>
</w:footnotes>
""",
            encoding="utf-8",
        )
        content_types = temp / "[Content_Types].xml"
        content_xml = content_types.read_text(encoding="utf-8")
        if "footnotes+xml" not in content_xml:
            content_xml = content_xml.replace(
                "</Types>",
                '<Override PartName="/word/footnotes.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.'
                'wordprocessingml.footnotes+xml"/></Types>',
            )
            content_types.write_text(content_xml, encoding="utf-8")
        rels = temp / "word/_rels/document.xml.rels"
        rels_xml = rels.read_text(encoding="utf-8")
        if "footnotes.xml" not in rels_xml:
            rels_xml = rels_xml.replace(
                "</Relationships>",
                '<Relationship Id="rIdCRAFootnotes" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                'relationships/footnotes" Target="footnotes.xml"/></Relationships>',
            )
            rels.write_text(rels_xml, encoding="utf-8")
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in sorted(temp.rglob("*")):
                if item.is_file():
                    archive.write(item, item.relative_to(temp).as_posix())


def _rule_paragraphs(document: Document, *, version: int) -> None:
    document.add_heading("Synthetic Rule Matrix", level=0)
    document.add_heading("1. Consent and screening", level=1)
    document.add_paragraph(
        "Rule R-SCREEN-01: Apply consent requirements before any study procedure."
    )
    document.add_paragraph(
        "Precondition: study_phase IN (screening, treatment)"
    )
    document.add_paragraph(
        "Trigger: screening_active = true AND consent_given = false"
    )
    document.add_paragraph(
        "Branch B: WHEN screening_active = true AND consent_given = false "
        "THEN obtain documented consent before procedures"
    )
    document.add_paragraph(
        "Branch F: WHEN emergency_treatment = true THEN follow emergency pathway"
    )
    if version == 1:
        document.add_paragraph(
            "Exception E1: WHEN emergency_treatment = true "
            "THEN emergency exception applies"
        )
    else:
        document.add_paragraph(
            "Exception E1: WHEN emergency_treatment = true "
            "THEN emergency exception applies"
        )
        document.add_paragraph(
            "Exception E3: WHEN consent_given = false "
            "THEN pause further non-emergency procedures"
        )
    document.add_paragraph(
        "Follow-up: document the exception rationale"
    )
    document.add_paragraph(
        "Completion: signed consent or documented emergency exception is present"
    )
    document.add_paragraph(
        "Required facts: study_phase, screening_active, consent_given, "
        "emergency_treatment"
    )
    if version == 1:
        document.add_heading("2. Visit timing", level=1)
        document.add_paragraph(
            "Rule R-VISIT-01: Visit 1 must occur within the permitted window."
        )
        document.add_paragraph("Trigger: present visit_1_due")
        document.add_paragraph(
            "Branch W: WHEN visit_date within -3..3 days of consent_date "
            "THEN record window as on time"
        )
        document.add_paragraph(
            "Branch OUT: WHEN visit_date within 4..30 days of consent_date "
            "THEN create follow-up"
        )
        document.add_paragraph(
            "Exception E2: WHEN protocol_waiver = true "
            "THEN follow the approved waiver"
        )
        document.add_paragraph(
            "Follow-up: record dates and source"
        )
        document.add_paragraph(
            "Completion: source dates are verified"
        )
        document.add_paragraph(
            "Required facts: visit_1_due, visit_date, consent_date, protocol_waiver"
        )
    document.add_heading("3. Background", level=1)
    document.add_paragraph(
        "This illustrative matrix is synthetic and is not a clinical protocol."
    )


def _inject_footnote(
    path: Path,
    *,
    target_text: str,
    footnote_text: str,
) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        with zipfile.ZipFile(path) as source:
            source.extractall(temp)
        document_xml = temp / "word/document.xml"
        xml = document_xml.read_text(encoding="utf-8")
        target = (
            "<w:p><w:r><w:t>"
            + target_text
            + "</w:t></w:r></w:p>"
        )
        if target not in xml:
            raise RuntimeError("footnote target paragraph not found")
        xml = xml.replace(
            target,
            (
                "<w:p><w:r><w:t>"
                + target_text
                + "</w:t></w:r>"
                '<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr>'
                '<w:footnoteReference w:id="7"/></w:r></w:p>'
            ),
            1,
        )
        document_xml.write_text(xml, encoding="utf-8")
        (temp / "word/footnotes.xml").write_text(
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>
  <w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>
  <w:footnote w:id="7"><w:p><w:r><w:t>"""
            + footnote_text
            + """</w:t></w:r></w:p></w:footnote>
</w:footnotes>
""",
            encoding="utf-8",
        )
        content_types = temp / "[Content_Types].xml"
        content_xml = content_types.read_text(encoding="utf-8")
        if "footnotes+xml" not in content_xml:
            content_xml = content_xml.replace(
                "</Types>",
                '<Override PartName="/word/footnotes.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.'
                'wordprocessingml.footnotes+xml"/></Types>',
            )
            content_types.write_text(content_xml, encoding="utf-8")
        rels = temp / "word/_rels/document.xml.rels"
        rels_xml = rels.read_text(encoding="utf-8")
        if "footnotes.xml" not in rels_xml:
            rels_xml = rels_xml.replace(
                "</Relationships>",
                '<Relationship Id="rIdCRAFootnotes" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                'relationships/footnotes" Target="footnotes.xml"/></Relationships>',
            )
            rels.write_text(rels_xml, encoding="utf-8")
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in sorted(temp.rglob("*")):
                if item.is_file():
                    archive.write(item, item.relative_to(temp).as_posix())


def _synthetic_rule_matrix(path: Path, *, version: int) -> None:
    document = Document()
    document.core_properties.title = f"Synthetic rule matrix v{version}"
    document.core_properties.author = "Synthetic fixture generator"
    document.core_properties.created = datetime(2026, 10, 31)
    document.core_properties.modified = datetime(2026, 10, 31)
    _rule_paragraphs(document, version=version)
    document.save(path)
    if version == 1:
        _inject_footnote(
            path,
            target_text=(
                "Rule R-VISIT-01: Visit 1 must occur within the permitted window."
            ),
            footnote_text=(
                "Synthetic footnote R-VISIT-01: day 3 is inclusive and day 4 "
                "is outside the on-time branch."
            ),
        )


def _synthetic_rule_evaluation(path: Path) -> None:
    document = Document()
    document.core_properties.title = "Independent synthetic rule evaluation"
    document.core_properties.author = "Synthetic fixture generator"
    document.core_properties.created = datetime(2026, 10, 31)
    document.core_properties.modified = datetime(2026, 10, 31)
    document.add_heading("Independent Rule Evaluation", level=0)
    document.add_heading("1. Laboratory", level=1)
    document.add_paragraph(
        "Rule R-LAB-01: Apply the synthetic local reference range policy."
    )
    document.add_paragraph(
        "Trigger: local_reference_ranges = true AND site_profile_complete = true"
    )
    document.add_paragraph(
        "Branch A: WHEN lab_value >= 10.5 THEN flag for CRA review"
    )
    document.add_paragraph(
        "Branch B: WHEN lab_value < 10.5 THEN retain as normal-range record"
    )
    document.add_paragraph(
        "Exception X: WHEN delegation_allowed = true "
        "THEN follow delegated review"
    )
    document.add_paragraph("Follow-up: compare the signed local range")
    document.add_paragraph("Completion: source range and value are verified")
    document.add_paragraph(
        "Required facts: local_reference_ranges, site_profile_complete, "
        "lab_value, delegation_allowed"
    )
    document.add_heading("2. Safety documentation", level=1)
    document.add_paragraph(
        "Rule R-SAFETY-01: Investigators must not record relatedness without "
        "a documented rationale."
    )
    document.add_paragraph("Trigger: ae_present = true")
    document.add_paragraph(
        "Branch N: WHEN relatedness_documented = false "
        "THEN request a documented rationale"
    )
    document.add_paragraph(
        "Exception Q: WHEN not_yet_assessed = true "
        "THEN retain relatedness as pending"
    )
    document.add_paragraph("Follow-up: keep medical conclusion separate")
    document.add_paragraph("Completion: documented rationale is available")
    document.add_paragraph(
        "Required facts: ae_present, relatedness_documented, not_yet_assessed"
    )
    document.save(path)


def _synthetic_pdf(path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.setTitle("Synthetic monitoring report")
    pdf.setAuthor("Synthetic fixture generator")
    width, height = A4
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(60, height - 70, "Synthetic Monitoring Report")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(60, height - 95, "Site: Synthetic Site A    Subject: SYN-001")
    pdf.drawString(60, height - 115, "This file contains no real clinical information.")
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(60, height - 155, "Laboratory review")
    text = "Verify the locally reported value against the synthetic EDC export."
    pdf.setFont("Helvetica", 11)
    pdf.drawString(60, height - 175, text)
    left, top, right, bottom = 60, height - 210, width - 60, height - 330
    widths = [100, 100, right - left - 200]
    heights = [30] * 4
    pdf.setLineWidth(0.8)
    y = top
    for row_height in heights:
        pdf.line(left, y, right, y)
        y -= row_height
    pdf.line(left, bottom, right, bottom)
    x = left
    for cell_width in widths:
        pdf.line(x, top, x, bottom)
        x += cell_width
    pdf.line(right, top, right, bottom)
    rows = [
        ("Analyte", "Result", "Comment"),
        ("Synthetic Hb", "121 g/L", "Within synthetic local range"),
        ("Synthetic ALT", "31 U/L", "Synthetic only"),
    ]
    for row_index, row in enumerate(rows):
        y = top - 20 - row_index * 30
        x = left + 8
        for column_index, value in enumerate(row):
            font = "Helvetica-Bold" if row_index == 0 else "Helvetica"
            pdf.setFont(font, 9)
            pdf.drawString(x, y, value)
            x += widths[column_index]
    pdf.showPage()
    pdf.save()


def _synthetic_xlsx(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Synthetic Carries"
    sheet.append(["Issue ID", "Description", "Status"])
    sheet.append(["CRA-SYN-001", "Synthetic carryover example", "Open"])
    sheet.append(["CRA-SYN-002", "Synthetic directory example", "Pending"])
    workbook.properties.creator = "Synthetic fixture generator"
    workbook.save(path)


def _synthetic_image(path: Path) -> None:
    image = Image.new("RGB", (1200, 600), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 1170, 570), outline="black", width=3)
    draw.text((70, 70), "SYNTHETIC LAB REPORT", fill="black")
    draw.text((70, 140), "Analyte      Result      Unit", fill="black")
    draw.text((70, 210), "SYNTH-Hb     121         g/L", fill="black")
    draw.text((70, 500), "NO REAL PATIENT DATA", fill="black")
    image.save(path)


def _hashes() -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(OUTPUT.iterdir())
        if path.is_file()
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for path in OUTPUT.glob("*"):
        if path.is_file():
            path.unlink()
    protocol = OUTPUT / "synthetic_rule_protocol.docx"
    _synthetic_docx(protocol)
    shutil.copy2(protocol, OUTPUT / "synthetic_report_template.docx")
    _synthetic_rule_matrix(OUTPUT / "synthetic_rule_matrix_v1.docx", version=1)
    _synthetic_rule_matrix(OUTPUT / "synthetic_rule_matrix_v2.docx", version=2)
    _synthetic_rule_evaluation(OUTPUT / "synthetic_rule_evaluation.docx")
    _synthetic_pdf(OUTPUT / "synthetic_monitoring_report.pdf")
    _synthetic_xlsx(OUTPUT / "synthetic_track.xlsx")
    _synthetic_image(OUTPUT / "synthetic_lab_report.png")
    (OUTPUT / "synthetic_rule_text.txt").write_text(
        "Rule R-EMAIL-01: Apply the synthetic email rule directly.\n"
        "Trigger: condition_c = true\n"
        "Branch B: WHEN condition_c = true THEN follow path B\n"
        "Completion: the named path is documented\n"
        "Required facts: condition_c\n",
        encoding="utf-8",
    )
    hashes = _hashes()
    manifest = {
        "schema_version": 1,
        "source": "pure_synthetic",
        "generated_on": str(date(2026, 10, 31)),
        "generator": "tests/fixtures/documents/generate_fixtures.py",
        "artifacts": [
            {
                "artifact_id": "RULE-DOCX-DEV",
                "file": "documents/artifacts/synthetic_rule_protocol.docx",
                "format": "docx",
                "purpose": "rule",
                "group": "development",
                "sha256": hashes["synthetic_rule_protocol.docx"],
                "expected": {
                    "anchors": [
                        "table_cell",
                        "footnote",
                        "paragraph",
                        "media",
                    ],
                    "section_path": ["Synthetic Study Protocol", "1. Screening"],
                    "background_tag": "CRA-BACKGROUND",
                    "bold_text": "any study procedure",
                    "footnote_text": "Synthetic footnote: applicability is illustrative only.",
                },
            },
            {
                "artifact_id": "REPORT-PDF-EVAL",
                "file": "documents/artifacts/synthetic_monitoring_report.pdf",
                "format": "pdf",
                "purpose": "carryover_report",
                "group": "evaluation",
                "sha256": hashes["synthetic_monitoring_report.pdf"],
                "expected": {
                    "page": 1,
                    "anchor_types": ["pdf_text", "table_cell"],
                    "contains": ["SYN-001", "Synthetic Hb"],
                    "coordinates_present": True,
                },
            },
            {
                "artifact_id": "TRACK-XLSX-DEV",
                "file": "documents/artifacts/synthetic_track.xlsx",
                "format": "xlsx",
                "purpose": "track",
                "group": "development",
                "sha256": hashes["synthetic_track.xlsx"],
                "expected": {
                    "retained_as_private_file": True,
                    "structured_parsing_task": "CRA-W07/W06",
                },
            },
            {
                "artifact_id": "LAB-PNG-PROBE",
                "file": "documents/artifacts/synthetic_lab_report.png",
                "format": "png",
                "purpose": "fact",
                "group": "development",
                "sha256": hashes["synthetic_lab_report.png"],
                "expected": {
                    "ocr_candidate_probe_only": True,
                    "minimum_expected_tokens": ["SYNTH-Hb", "121", "g/L"],
                },
            },
            {
                "artifact_id": "TEMPLATE-DOCX-DEV",
                "file": "documents/artifacts/synthetic_report_template.docx",
                "format": "docx",
                "purpose": "template",
                "group": "development",
                "sha256": hashes["synthetic_report_template.docx"],
                "expected": {"retained_as_private_file": True},
            },
            {
                "artifact_id": "RULE-TEXT-DEV",
                "file": "documents/artifacts/synthetic_rule_text.txt",
                "format": "txt",
                "purpose": "rule",
                "group": "development",
                "sha256": hashes["synthetic_rule_text.txt"],
                "expected": {
                    "anchor_types": ["plain_text"],
                    "contains": ["R-EMAIL-01", "condition_c", "path B"],
                    "direct_accept": True,
                },
            },
            {
                "artifact_id": "RULE-DOCX-V1-DEV",
                "file": "documents/artifacts/synthetic_rule_matrix_v1.docx",
                "format": "docx",
                "purpose": "rule",
                "group": "development",
                "sha256": hashes["synthetic_rule_matrix_v1.docx"],
                "expected": {
                    "rule_keys": ["R-SCREEN-01", "R-VISIT-01"],
                    "footnote_rule": "R-VISIT-01",
                    "exception_count": 2,
                    "analysis_required": False,
                },
            },
            {
                "artifact_id": "RULE-DOCX-V2-DEV",
                "file": "documents/artifacts/synthetic_rule_matrix_v2.docx",
                "format": "docx",
                "purpose": "rule",
                "group": "development",
                "sha256": hashes["synthetic_rule_matrix_v2.docx"],
                "expected": {
                    "rule_keys": ["R-SCREEN-01"],
                    "omitted_prior_rule": "R-VISIT-01",
                    "new_exception": "E3",
                },
            },
            {
                "artifact_id": "RULE-DOCX-EVAL",
                "file": "documents/artifacts/synthetic_rule_evaluation.docx",
                "format": "docx",
                "purpose": "rule",
                "group": "evaluation",
                "sha256": hashes["synthetic_rule_evaluation.docx"],
                "expected": {
                    "rule_keys": ["R-LAB-01", "R-SAFETY-01"],
                    "evaluation_cases": "rules/evaluation_cases.json",
                },
            },
        ],
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
