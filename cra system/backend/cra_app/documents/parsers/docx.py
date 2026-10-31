"""Controlled OOXML DOCX parser preserving logical source locations."""
from __future__ import annotations

import hashlib
import posixpath
import zipfile
from dataclasses import dataclass
from io import BytesIO

from lxml import etree

from cra_app.providers.ports import CoverageUnit, ParsedAnchor, ParseResult

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


@dataclass
class _BuildContext:
    anchors: list[ParsedAnchor]
    coverage: list[CoverageUnit]
    ordinal: int
    section_path: list[str]
    table_index: int
    tags: tuple[str, ...] = ()

    def next_ordinal(self) -> int:
        value = self.ordinal
        self.ordinal += 1
        return value


def _qname(local: str) -> str:
    return f"{{{W}}}{local}"


def _attribute(element: etree._Element, local: str) -> str | None:
    return element.get(_qname(local))


def _style_map(archive: zipfile.ZipFile) -> dict[str, dict[str, object]]:
    try:
        root = etree.fromstring(archive.read("word/styles.xml"))
    except KeyError:
        return {}
    result: dict[str, dict[str, object]] = {}
    for style in root.findall("w:style", NS):
        style_id = _attribute(style, "styleId")
        if not style_id:
            continue
        based_on = style.find("w:basedOn", NS)
        result[style_id] = {
            "name": _attribute(style.find("w:name", NS), "val")
            if style.find("w:name", NS) is not None
            else style_id,
            "based_on": _attribute(based_on, "val") if based_on is not None else None,
            "bold": style.find("w:rPr/w:b", NS) is not None,
            "italic": style.find("w:rPr/w:i", NS) is not None,
            "underline": style.find("w:rPr/w:u", NS) is not None,
        }
    return result


def _resolved_style(
    style_id: str | None, styles: dict[str, dict[str, object]]
) -> dict[str, object]:
    if not style_id or style_id not in styles:
        return {
            "style_id": style_id,
            "style_name": style_id,
            "bold": False,
            "italic": False,
            "underline": False,
        }
    chain = []
    cursor = style_id
    seen: set[str] = set()
    while cursor and cursor in styles and cursor not in seen:
        seen.add(cursor)
        chain.append(styles[cursor])
        cursor = str(styles[cursor].get("based_on") or "")
    merged: dict[str, object] = {}
    for item in reversed(chain):
        merged.update({key: value for key, value in item.items() if value is not None})
    inherited_bold = bool(merged.get("bold", False))
    inherited_italic = bool(merged.get("italic", False))
    inherited_underline = bool(merged.get("underline", False))
    return {
        "style_id": style_id,
        "style_name": merged.get("name", style_id),
        "bold": inherited_bold,
        "italic": inherited_italic,
        "underline": inherited_underline,
        "based_on": chain[-1].get("based_on") if chain else None,
    }


def _runtime_style(
    run: etree._Element,
    paragraph_style: dict[str, object],
) -> dict[str, object]:
    rpr = run.find("w:rPr", NS)
    style = dict(paragraph_style)
    if rpr is not None:
        if rpr.find("w:b", NS) is not None:
            style["bold"] = True
        if rpr.find("w:i", NS) is not None:
            style["italic"] = True
        if rpr.find("w:u", NS) is not None:
            style["underline"] = True
        color = rpr.find("w:color", NS)
        if color is not None:
            style["color"] = _attribute(color, "val")
        size = rpr.find("w:sz", NS)
        if size is not None:
            style["font_size_half_points"] = _attribute(size, "val")
    run_style = rpr.find("w:rStyle", NS) if rpr is not None else None
    if run_style is not None:
        style["run_style_id"] = _attribute(run_style, "val")
    return style


def _paragraph_content(
    paragraph: etree._Element,
    styles: dict[str, dict[str, object]],
) -> tuple[str, dict[str, object], list[dict[str, object]]]:
    ppr = paragraph.find("w:pPr", NS)
    pstyle = ppr.find("w:pStyle", NS) if ppr is not None else None
    style_id = _attribute(pstyle, "val") if pstyle is not None else None
    paragraph_style = _resolved_style(style_id, styles)
    text_parts: list[str] = []
    runs: list[dict[str, object]] = []
    for child in paragraph.iterchildren():
        if child.tag == _qname("r"):
            fragment = "".join(
                part.text or ""
                for part in child.iter()
                if part.tag in {_qname("t"), _qname("instrText")}
            )
            if fragment:
                text_parts.append(fragment)
                runs.append(
                    {
                        "text": fragment,
                        **_runtime_style(child, paragraph_style),
                    }
                )
            elif child.find("w:tab", NS) is not None:
                text_parts.append("\t")
            elif child.find("w:br", NS) is not None:
                text_parts.append("\n")
        elif child.tag == _qname("hyperlink"):
            for run in child.findall("w:r", NS):
                fragment = "".join(
                    node.text or "" for node in run.findall("w:t", NS)
                )
                if fragment:
                    text_parts.append(fragment)
                    runs.append(
                        {
                            "text": fragment,
                            **_runtime_style(run, paragraph_style),
                        }
                    )
    pstyle_name = str(paragraph_style.get("style_name") or "")
    heading_level = None
    if pstyle_name.lower().startswith("heading "):
        try:
            heading_level = int(pstyle_name.split()[-1])
        except ValueError:
            heading_level = None
    elif pstyle_name == "Title":
        heading_level = 1
    style = {**paragraph_style, "runs": runs}
    if heading_level:
        style["heading_level"] = heading_level
    return "".join(text_parts), style, runs


def _coverage(
    context: _BuildContext,
    unit_key: str,
    unit_type: str,
    status: str,
    *,
    reason: str | None = None,
    anchor_key: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    context.coverage.append(
        CoverageUnit(
            unit_key=unit_key,
            unit_type=unit_type,
            status=status,  # type: ignore[arg-type]
            reason=reason,
            anchor_key=anchor_key,
            metadata=metadata or {},
        )
    )


def _add_paragraph(
    paragraph: etree._Element,
    *,
    context: _BuildContext,
    logical_node_id: str,
    styles: dict[str, dict[str, object]],
    anchor_type: str = "paragraph",
    table_index: int | None = None,
    row_index: int | None = None,
    column_index: int | None = None,
    extra_style: dict[str, object] | None = None,
) -> None:
    text, style, _ = _paragraph_content(paragraph, styles)
    if extra_style:
        style.update(extra_style)
    heading_level = style.get("heading_level")
    if isinstance(heading_level, int) and text.strip():
        context.section_path[:] = (
            context.section_path[: heading_level - 1] + [text.strip()]
        )
    is_background = any("background" in tag.lower() or "背景" in tag for tag in context.tags)
    if not text.strip():
        _coverage(
            context,
            f"{logical_node_id}:coverage",
            "paragraph",
            "not_applicable",
            reason="empty paragraph",
            metadata={"anchor_type": anchor_type},
        )
        return
    anchor = ParsedAnchor(
        anchor_type=anchor_type,
        logical_node_id=logical_node_id,
        text=text,
        ordinal=context.next_ordinal(),
        section_path=list(context.section_path),
        style=style,
        table_index=table_index,
        row_index=row_index,
        column_index=column_index,
        metadata={"content_control_tags": list(context.tags)},
    )
    context.anchors.append(anchor)
    _coverage(
        context,
        f"{logical_node_id}:coverage",
        "paragraph",
        "background" if is_background else "processed",
        reason="explicit background content control" if is_background else None,
        anchor_key=logical_node_id,
        metadata={"anchor_type": anchor_type},
    )


def _cell_grid_span(cell: etree._Element) -> int:
    span = cell.find("w:tcPr/w:gridSpan", NS)
    if span is None:
        return 1
    try:
        return max(1, int(_attribute(span, "val") or "1"))
    except ValueError:
        return 1


def _cell_vertical_merge(cell: etree._Element) -> str | None:
    merge = cell.find("w:tcPr/w:vMerge", NS)
    if merge is None:
        return None
    return _attribute(merge, "val") or "continue"


def _add_table(
    table: etree._Element,
    *,
    context: _BuildContext,
    table_path: str,
    styles: dict[str, dict[str, object]],
) -> None:
    context.table_index += 1
    table_index = context.table_index
    for row_index, row in enumerate(table.findall("w:tr", NS), start=1):
        grid_column = 0
        for cell_index, cell in enumerate(row.findall("w:tc", NS), start=1):
            span = _cell_grid_span(cell)
            merge = _cell_vertical_merge(cell)
            grid_column += 1
            cell_path = (
                f"{table_path}/r[{row_index}]/c[{cell_index}]"
            )
            paragraphs = cell.findall("w:p", NS)
            if not paragraphs:
                _coverage(
                    context,
                    f"{cell_path}:coverage",
                    "table_cell",
                    "not_applicable",
                    reason="table cell has no paragraph",
                    metadata={
                        "table_index": table_index,
                        "row_index": row_index,
                        "grid_column": grid_column,
                        "grid_span": span,
                        "vertical_merge": merge,
                    },
                )
            for paragraph_index, paragraph in enumerate(paragraphs, start=1):
                _add_paragraph(
                    paragraph,
                    context=context,
                    logical_node_id=f"{cell_path}/p[{paragraph_index}]",
                    styles=styles,
                    anchor_type="table_cell",
                    table_index=table_index,
                    row_index=row_index,
                    column_index=grid_column,
                    extra_style={
                        "grid_span": span,
                        "vertical_merge": merge,
                        "cell_index": cell_index,
                    },
                )
            grid_column += span - 1


def _add_blocks(
    container: etree._Element,
    *,
    context: _BuildContext,
    base_path: str,
    styles: dict[str, dict[str, object]],
) -> None:
    paragraph_index = 0
    table_index = 0
    sdt_index = 0
    other_index = 0
    for child in container:
        if child.tag == _qname("p"):
            paragraph_index += 1
            _add_paragraph(
                child,
                context=context,
                logical_node_id=f"{base_path}/p[{paragraph_index}]",
                styles=styles,
            )
        elif child.tag == _qname("tbl"):
            table_index += 1
            _add_table(
                child,
                context=context,
                table_path=f"{base_path}/table[{table_index}]",
                styles=styles,
            )
        elif child.tag == _qname("sdt"):
            sdt_index += 1
            sdt_path = f"{base_path}/sdt[{sdt_index}]"
            properties = child.find("w:sdtPr", NS)
            tags: list[str] = []
            if properties is not None:
                for label in ("tag", "alias"):
                    node = properties.find(f"w:{label}", NS)
                    if node is not None:
                        value = _attribute(node, "val")
                        if value:
                            tags.append(value)
            content = child.find("w:sdtContent", NS)
            if content is None:
                _coverage(
                    context,
                    f"{sdt_path}:coverage",
                    "content_control",
                    "unsupported",
                    reason="content control has no readable content",
                    metadata={"tags": tags},
                )
                continue
            previous_tags = context.tags
            context.tags = (*context.tags, *tags)
            _add_blocks(
                content,
                context=context,
                base_path=sdt_path,
                styles=styles,
            )
            context.tags = previous_tags
        elif child.tag not in {
            _qname("sectPr"),
            _qname("bookmarkStart"),
            _qname("bookmarkEnd"),
        }:
            other_index += 1
            _coverage(
                context,
                f"{base_path}/other[{other_index}]",
                "ooxml_element",
                "unsupported",
                reason=f"unhandled OOXML element {etree.QName(child).localname}",
            )


def _add_footnotes(
    archive: zipfile.ZipFile,
    *,
    context: _BuildContext,
    styles: dict[str, dict[str, object]],
) -> None:
    try:
        root = etree.fromstring(archive.read("word/footnotes.xml"))
    except KeyError:
        return
    for note in root.findall("w:footnote", NS):
        footnote_id = _attribute(note, "id")
        if not footnote_id or footnote_id in {"-1", "0"}:
            continue
        paragraphs = note.findall("w:p", NS)
        for index, paragraph in enumerate(paragraphs, start=1):
            text, style, _ = _paragraph_content(paragraph, styles)
            if not text.strip():
                continue
            anchor_key = f"footnote[{footnote_id}]/p[{index}]"
            context.anchors.append(
                ParsedAnchor(
                    anchor_type="footnote",
                    logical_node_id=anchor_key,
                    text=text,
                    ordinal=context.next_ordinal(),
                    section_path=list(context.section_path),
                    style=style,
                    footnote_id=footnote_id,
                )
            )
            _coverage(
                context,
                f"{anchor_key}:coverage",
                "footnote",
                "processed",
                anchor_key=anchor_key,
                metadata={"footnote_id": footnote_id},
            )


def _add_header_footer_parts(
    archive: zipfile.ZipFile,
    *,
    context: _BuildContext,
    styles: dict[str, dict[str, object]],
) -> None:
    names = sorted(
        name
        for name in archive.namelist()
        if name.startswith("word/header") or name.startswith("word/footer")
    )
    for part_name in names:
        root = etree.fromstring(archive.read(part_name))
        common = posixpath.basename(part_name)
        type_name = "header" if "/header" in part_name else "footer"
        previous_path = list(context.section_path)
        context.section_path = [type_name.title(), common]
        _add_blocks(
            root,
            context=context,
            base_path=f"{type_name}[{common}]",
            styles=styles,
        )
        context.section_path = previous_path


def _add_media_coverage(
    archive: zipfile.ZipFile, context: _BuildContext
) -> None:
    media = sorted(
        name for name in archive.namelist() if name.startswith("word/media/")
    )
    for index, name in enumerate(media, start=1):
        content = archive.read(name)
        anchor_key = f"media[{index}]/{posixpath.basename(name)}"
        context.anchors.append(
            ParsedAnchor(
                anchor_type="media",
                logical_node_id=anchor_key,
                text=posixpath.basename(name),
                ordinal=context.next_ordinal(),
                section_path=list(context.section_path),
                style={
                    "media_path": name,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "size_bytes": len(content),
                },
            )
        )
        _coverage(
            context,
            f"{anchor_key}:coverage",
            "embedded_media",
            "unsupported",
            reason="embedded media retained but not OCR-parsed in W03",
            anchor_key=anchor_key,
            metadata={"path": name, "size_bytes": len(content)},
        )


class DocxSourceParser:
    name = "ooxml-docx"
    version = "1"

    def supports(self, media_type: str, filename: str) -> bool:
        return media_type == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ) and filename.lower().endswith(".docx")

    def parse(
        self, content: bytes, *, media_type: str, filename: str
    ) -> ParseResult:
        try:
            archive = zipfile.ZipFile(BytesIO(content))
            archive.testzip()
            if "word/document.xml" not in archive.namelist():
                raise ValueError("missing word/document.xml")
            if any(name.lower().endswith("vbaproject.bin") for name in archive.namelist()):
                raise ValueError("macro-enabled documents are not accepted")
            styles = _style_map(archive)
            root = etree.fromstring(archive.read("word/document.xml"))
            body = root.find("w:body", NS)
            if body is None:
                raise ValueError("DOCX body is missing")
            context = _BuildContext(
                anchors=[],
                coverage=[],
                ordinal=0,
                section_path=[],
                table_index=0,
            )
            _add_blocks(
                body,
                context=context,
                base_path="body",
                styles=styles,
            )
            _add_footnotes(archive, context=context, styles=styles)
            _add_header_footer_parts(archive, context=context, styles=styles)
            _add_media_coverage(archive, context)
            unsupported = any(
                unit.status in {"unsupported", "failed"} for unit in context.coverage
            )
            status = "partial" if unsupported or not context.anchors else "completed"
            return ParseResult(
                parser_name=self.name,
                parser_version=self.version,
                anchors=tuple(context.anchors),
                coverage=tuple(context.coverage),
                status=status,
                warnings=(
                    ("embedded or unsupported OOXML content was retained as coverage",)
                    if unsupported
                    else ()
                ),
            )
        except Exception as exc:
            return ParseResult(
                parser_name=self.name,
                parser_version=self.version,
                anchors=(),
                coverage=(
                    CoverageUnit(
                        unit_key="document",
                        unit_type="document",
                        status="failed",
                        reason=f"{type(exc).__name__}: {exc}"[:500],
                    ),
                ),
                status="failed",
                warnings=("DOCX parsing failed",),
            )
