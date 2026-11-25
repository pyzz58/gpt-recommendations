from __future__ import annotations

import io

import pytest
from openpyxl import Workbook
from pydantic import ValidationError

from medical_one_person.domain.datasets import CleaningSpec
from medical_one_person.infrastructure.tables import TableImportError, parse_table


def test_csv_import_preserves_missing_values() -> None:
    parsed = parse_table(
        b"group,score\ncontrol,10\ntreatment,\n",
        filename="synthetic.csv",
        media_type="text/csv",
    )
    assert parsed.columns == ["group", "score"]
    assert parsed.rows[1]["score"] is None
    assert parsed.quality_findings[0]["code"] == "MISSING_VALUES"


def test_duplicate_headers_and_formulas_are_rejected() -> None:
    with pytest.raises(TableImportError, match="unique"):
        parse_table(
            b"score,score\n1,2\n",
            filename="duplicate.csv",
            media_type="text/csv",
        )

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["group", "score"])
    worksheet.append(["control", "=1+2"])
    content = io.BytesIO()
    workbook.save(content)
    with pytest.raises(TableImportError, match="no independently evaluated"):
        parse_table(
            content.getvalue(),
            filename="formula.xlsx",
            media_type=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        )


def test_cleaning_cannot_create_duplicate_columns() -> None:
    with pytest.raises(ValidationError, match="duplicate output columns"):
        CleaningSpec(
            select_columns=["score", "value"],
            numeric_columns=["score"],
            rename_columns={"value": "score"},
            drop_missing_columns=[],
            rationale="错误映射测试。",
        )
