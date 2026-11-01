"""Generate deterministic synthetic W11 DOCX and XLSX templates."""
from __future__ import annotations

from pathlib import Path

from docx import Document
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"


def word_template(filename: str, title: str, loops: list[tuple[str, str]]) -> None:
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "PingFang SC"
    heading = document.add_heading(title, level=1)
    heading.style = document.styles["Title"]
    document.add_paragraph("项目 {{ study_code }} · 中心 {{ site_code }} · {{ site_name }}")
    document.add_paragraph("{{ visit_title }} · {{ generated_on }}")
    document.add_paragraph("核查范围：{{ visit_scope_note }}")
    document.add_paragraph("{{ coverage_summary }}")
    for loop_name, label in loops:
        document.add_heading(label, level=2)
        document.add_paragraph("{% for issue in " + loop_name + " %}")
        document.add_paragraph(
            "{{ issue.issue_number }} | {{ issue.original_finding }} | "
            "{{ issue.location }} | {{ issue.known_progress }}"
        )
        document.add_paragraph(
            "整改建议：{{ issue.recommendation }}；来源：{{ issue.source_refs_text }}"
        )
        document.add_paragraph("{% endfor %}")
    document.add_paragraph("未核查/unknown：{{ not_checked_summary }}")
    document.add_paragraph("后续事项：{{ next_steps_summary }}")
    document.add_paragraph("用户说明：{{ user_summary }}")
    document.add_paragraph("用户结论：{{ user_conclusion }}")
    document.save(ARTIFACTS / filename)


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    word_template(
        "synthetic_visit_letter.docx",
        "合成监查访视信",
        [("letter_issues", "本次选取的遗留事项")],
    )
    word_template(
        "synthetic_monitoring_report.docx",
        "合成中心监查报告",
        [
            ("prior_issues", "上次问题处理"),
            ("current_findings", "本次发现"),
        ],
    )
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Track"
    headers = [
        "Issue",
        "Section",
        "Finding",
        "Location",
        "Recommendation",
        "Status",
        "Progress",
        "Next step",
        "Source",
    ]
    for column, header in enumerate(headers, start=1):
        cell = sheet.cell(row=1, column=column, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="365F91")
    widths = [16, 18, 36, 24, 32, 18, 32, 32, 28]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[chr(64 + index)].width = width
    workbook.save(ARTIFACTS / "synthetic_track_template.xlsx")


if __name__ == "__main__":
    main()
