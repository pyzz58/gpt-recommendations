"""Plain-text parser preserving line positions."""
from __future__ import annotations

from cra_app.providers.ports import CoverageUnit, ParsedAnchor, ParseResult


class TextSourceParser:
    name = "utf8-text"
    version = "1"

    def supports(self, media_type: str, filename: str) -> bool:
        return media_type.startswith("text/") or filename.lower().endswith(".txt")

    def parse(
        self, content: bytes, *, media_type: str, filename: str
    ) -> ParseResult:
        try:
            text = content.decode("utf-8-sig")
            if "\x00" in text:
                raise ValueError("binary null byte in text source")
            anchors = []
            coverage = []
            for index, line in enumerate(text.splitlines(), start=1):
                key = f"line[{index}]"
                if not line.strip():
                    coverage.append(
                        CoverageUnit(
                            unit_key=f"{key}:coverage",
                            unit_type="text_line",
                            status="not_applicable",
                            reason="empty line",
                        )
                    )
                    continue
                anchors.append(
                    ParsedAnchor(
                        anchor_type="plain_text",
                        logical_node_id=key,
                        text=line,
                        ordinal=index - 1,
                    )
                )
                coverage.append(
                    CoverageUnit(
                        unit_key=f"{key}:coverage",
                        unit_type="text_line",
                        status="processed",
                        anchor_key=key,
                    )
                )
            return ParseResult(
                parser_name=self.name,
                parser_version=self.version,
                anchors=tuple(anchors),
                coverage=tuple(coverage),
                status="completed" if anchors else "failed",
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
                warnings=("Text parsing failed",),
            )
