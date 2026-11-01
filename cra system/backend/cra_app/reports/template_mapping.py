"""Declared template fields, loop regions and safe placeholder validation."""
from __future__ import annotations

import html
import re
import zipfile
from io import BytesIO
from typing import Any, Literal

from docxtpl import DocxTemplate
from jinja2.sandbox import SandboxedEnvironment
from openpyxl import load_workbook
from pydantic import BaseModel, ConfigDict, Field, model_validator

OutputKind = Literal["letter", "report", "track"]
OutputFormat = Literal["docx", "xlsx"]

CONTEXT_FIELDS = (
    "title",
    "study_code",
    "site_code",
    "site_name",
    "visit_title",
    "visit_stage",
    "visit_scope_note",
    "generated_on",
    "prior_issue_count",
    "current_finding_count",
    "selected_issue_count",
    "coverage_summary",
    "coverage_scope",
    "unknown_summary",
    "not_checked_summary",
    "next_steps_summary",
    "user_summary",
    "user_conclusion",
)

LOOP_FIELDS = {
    "letter_issues": (
        "issue_number",
        "original_finding",
        "location",
        "recommendation",
        "known_progress",
        "status",
        "next_steps_text",
        "source_refs_text",
    ),
    "prior_issues": (
        "issue_number",
        "original_finding",
        "location",
        "recommendation",
        "known_progress",
        "status",
        "next_steps_text",
        "source_refs_text",
    ),
    "current_findings": (
        "issue_number",
        "original_finding",
        "location",
        "recommendation",
        "known_progress",
        "status",
        "next_steps_text",
        "source_refs_text",
    ),
    "coverage_records": (
        "subject_label",
        "category",
        "scope_key",
        "status",
        "checked_through",
        "unverified_scope_text",
        "normal_scope_note",
    ),
    "next_steps": (
        "issue_number",
        "action_key",
        "kind",
        "status",
        "requirement",
    ),
    "safety_assessments": (
        "subject_label",
        "event_type",
        "event_date",
        "status",
        "questions_text",
        "unknowns_text",
    ),
    "track_rows": (
        "issue_number",
        "section",
        "original_finding",
        "location",
        "recommendation",
        "status",
        "known_progress",
        "next_steps_text",
        "source_refs_text",
    ),
}


class ReportContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DocxTemplateMapping(ReportContract):
    fields: dict[str, str] = Field(default_factory=dict, max_length=100)
    loops: dict[str, str] = Field(default_factory=dict, max_length=20)
    required_variables: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_paths(self) -> "DocxTemplateMapping":
        for template_name, path in self.fields.items():
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", template_name):
                raise ValueError(f"unsafe DOCX field name: {template_name}")
            if path not in CONTEXT_FIELDS:
                raise ValueError(f"unsupported DOCX context field: {path}")
        for loop_name, iterable in self.loops.items():
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", loop_name):
                raise ValueError(f"unsafe DOCX loop name: {loop_name}")
            if iterable not in LOOP_FIELDS:
                raise ValueError(f"unsupported DOCX loop source: {iterable}")
        unknown_required = set(self.required_variables) - set(self.fields)
        if unknown_required:
            raise ValueError(
                "required_variables must name declared DOCX fields: "
                + ", ".join(sorted(unknown_required))
            )
        return self


class XlsxTableMapping(ReportContract):
    sheet: str = Field(min_length=1, max_length=64)
    start_row: int = Field(ge=1)
    columns: dict[str, str] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def validate_columns(self) -> "XlsxTableMapping":
        for column, field in self.columns.items():
            if not re.fullmatch(r"[A-Z]{1,3}", column):
                raise ValueError(f"invalid Excel column: {column}")
            if field not in LOOP_FIELDS["track_rows"]:
                raise ValueError(f"unsupported track field: {field}")
        return self


class XlsxTemplateMapping(ReportContract):
    cells: dict[str, str] = Field(default_factory=dict, max_length=100)
    table: XlsxTableMapping | None = None
    required_variables: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_cells(self) -> "XlsxTemplateMapping":
        for coordinate, path in self.cells.items():
            if not re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]*", coordinate):
                raise ValueError(f"invalid Excel cell: {coordinate}")
            if path not in CONTEXT_FIELDS:
                raise ValueError(f"unsupported Excel context field: {path}")
        unknown_required = set(self.required_variables) - set(self.cells)
        if unknown_required:
            raise ValueError(
                "required_variables must name declared Excel cells: "
                + ", ".join(sorted(unknown_required))
            )
        return self


class TemplateMappingSpec(ReportContract):
    output_kind: OutputKind
    output_format: OutputFormat
    docx: DocxTemplateMapping | None = None
    xlsx: XlsxTemplateMapping | None = None

    @model_validator(mode="after")
    def validate_format(self) -> "TemplateMappingSpec":
        if self.output_format == "docx":
            if self.docx is None or self.xlsx is not None:
                raise ValueError("DOCX mapping and format must match")
            if self.output_kind == "track":
                raise ValueError("track output uses XLSX")
        else:
            if self.xlsx is None or self.docx is not None:
                raise ValueError("XLSX mapping and format must match")
        return self

    def required_variables(self) -> list[str]:
        if self.docx is not None:
            return list(self.docx.required_variables)
        assert self.xlsx is not None
        return list(self.xlsx.required_variables)

    def supported_fields(self) -> list[str]:
        if self.docx is not None:
            return sorted(self.docx.fields)
        assert self.xlsx is not None
        values = sorted(self.xlsx.cells)
        if self.xlsx.table is not None:
            values.extend(
                f"table.{column}" for column in self.xlsx.table.columns
            )
        return values


def _docx_xml(template_bytes: bytes) -> list[str]:
    try:
        with zipfile.ZipFile(BytesIO(template_bytes)) as archive:
            names = [
                name
                for name in archive.namelist()
                if name == "word/document.xml"
                or re.fullmatch(
                    r"word/(?:header|footer)[0-9]+\.xml", name
                )
            ]
            return [
                html.unescape(archive.read(name).decode("utf-8"))
                for name in names
            ]
    except (zipfile.BadZipFile, UnicodeDecodeError) as exc:
        raise ValueError("DOCX template is not a readable OOXML file") from exc


def validate_docx_template(
    template_bytes: bytes, mapping: DocxTemplateMapping
) -> None:
    active_loops: dict[str, str] = {}
    loop_stack: list[str] = []
    loop_pattern = re.compile(
        r"(?:[prt]+\s+)?for\s+([A-Za-z][A-Za-z0-9_]*)\s+in\s+"
        r"([A-Za-z][A-Za-z0-9_]*)"
    )
    for xml in _docx_xml(template_bytes):
        token_pattern = re.compile(
            r"({{\s*([^{}]+?)\s*}}|{%\s*([^{}]+?)\s*%})"
        )
        for token in token_pattern.finditer(xml):
            full = token.group(1)
            if full.startswith("{{"):
                path = str(token.group(2)).strip()
                if not re.fullmatch(
                    r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)?",
                    path,
                ):
                    raise ValueError(
                        f"unsafe DOCX variable expression: {path}"
                    )
                root, _, child = path.partition(".")
                if root in mapping.fields and not child:
                    continue
                if root in active_loops:
                    loop_source = active_loops[root]
                    if child and child in LOOP_FIELDS.get(
                        loop_source or "", ()
                    ):
                        continue
                raise ValueError(
                    f"undeclared or unsafe DOCX variable: {path}"
                )
                continue
            expression = str(token.group(3)).strip()
            if expression == "endfor":
                if not loop_stack:
                    raise ValueError("DOCX template has unmatched endfor")
                active_loops.pop(loop_stack.pop())
                continue
            match = loop_pattern.fullmatch(expression)
            if not match:
                raise ValueError(
                    f"unsupported DOCX control tag: {expression}"
                )
            variable, iterable = match.groups()
            if mapping.loops.get(iterable) != iterable:
                raise ValueError(
                    f"DOCX loop source is not declared: {iterable}"
                )
            active_loops[variable] = iterable
            loop_stack.append(variable)
    if loop_stack:
        raise ValueError("DOCX template has an unclosed loop")
    DocxTemplate(BytesIO(template_bytes))


def validate_xlsx_template(
    template_bytes: bytes, mapping: XlsxTemplateMapping
) -> None:
    try:
        workbook = load_workbook(BytesIO(template_bytes), data_only=False)
    except Exception as exc:
        raise ValueError("XLSX template is not a readable workbook") from exc
    try:
        for coordinate in mapping.cells:
            sheet_name = mapping.table.sheet if mapping.table else None
            if sheet_name is not None:
                if sheet_name not in workbook.sheetnames:
                    raise ValueError(
                        f"XLSX sheet is missing: {sheet_name}"
                    )
        if mapping.table is not None:
            if mapping.table.sheet not in workbook.sheetnames:
                raise ValueError(
                    f"XLSX sheet is missing: {mapping.table.sheet}"
                )
    finally:
        workbook.close()


def docx_render_context(
    mapping: DocxTemplateMapping, context: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    rendered: dict[str, Any] = {}
    missing: list[str] = []
    for name, source_path in mapping.fields.items():
        value = context.get(source_path)
        if value is None or value == "":
            rendered[name] = "unknown"
            if name in mapping.required_variables:
                missing.append(name)
        else:
            rendered[name] = value
    for loop_name, source_path in mapping.loops.items():
        rendered[loop_name] = context.get(source_path, [])
    return rendered, missing


def render_docx(
    template_bytes: bytes,
    mapping: DocxTemplateMapping,
    context: dict[str, Any],
) -> tuple[bytes, list[str]]:
    validate_docx_template(template_bytes, mapping)
    render_context, missing = docx_render_context(mapping, context)
    template = DocxTemplate(BytesIO(template_bytes))
    environment = SandboxedEnvironment(autoescape=False)
    template.render(render_context, environment)
    output = BytesIO()
    template.save(output)
    return output.getvalue(), missing


def _excel_safe(value: Any) -> Any:
    if isinstance(value, str) and value[:1] in {"=", "+", "-", "@"}:
        return "'" + value
    if isinstance(value, list):
        return "；".join(str(item) for item in value)
    if isinstance(value, dict):
        return "；".join(f"{key}: {item}" for key, item in value.items())
    return value


def render_xlsx(
    template_bytes: bytes,
    mapping: XlsxTemplateMapping,
    context: dict[str, Any],
) -> tuple[bytes, list[str], list[dict[str, Any]]]:
    validate_xlsx_template(template_bytes, mapping)
    workbook = load_workbook(BytesIO(template_bytes), data_only=False)
    missing: list[str] = []
    row_refs: list[dict[str, Any]] = []
    try:
        for coordinate, source_path in mapping.cells.items():
            value = context.get(source_path)
            if value is None or value == "":
                value = "unknown"
                if coordinate in mapping.required_variables:
                    missing.append(coordinate)
            sheet = (
                workbook[mapping.table.sheet]
                if mapping.table is not None
                else workbook.active
            )
            sheet[coordinate] = _excel_safe(value)
        if mapping.table is not None:
            worksheet = workbook[mapping.table.sheet]
            rows = context.get("track_rows", [])
            if not isinstance(rows, list):
                rows = []
            for offset, row in enumerate(rows):
                excel_row = mapping.table.start_row + offset
                for column, field in mapping.table.columns.items():
                    cell = worksheet[f"{column}{excel_row}"]
                    cell.value = _excel_safe(row.get(field, "unknown"))
                row_refs.append(
                    {
                        "row": excel_row,
                        "issue_number": row.get("issue_number"),
                        "section": row.get("section"),
                    }
                )
        output = BytesIO()
        workbook.save(output)
        return output.getvalue(), missing, row_refs
    finally:
        workbook.close()
