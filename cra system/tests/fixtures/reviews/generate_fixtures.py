"""Generate two synthetic report templates with distinct sections/questions."""
from __future__ import annotations

from pathlib import Path

from docx import Document

OUTPUT = Path(__file__).resolve().parent / "artifacts"


def build(
    filename: str,
    title: str,
    sections: list[tuple[str, list[str]]],
) -> None:
    document = Document()
    document.add_heading(title, level=0)
    document.add_paragraph("纯合成监查模板，仅用于本机工作台验收。")
    for heading, questions in sections:
        document.add_heading(heading, level=1)
        for question in questions:
            document.add_paragraph(question)
    document.save(OUTPUT / filename)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    build(
        "synthetic_monitoring_review_v1.docx",
        "合成中心监查报告核查模板 V1",
        [
            (
                "1. 知情同意与受试者资格",
                [
                    "知情同意签署日期是否早于或等于首次研究操作日期？",
                    "入排标准是否有来源记录并可追溯？",
                ],
            ),
            (
                "2. EDC与检验原始报告",
                [
                    "EDC检验值是否与原始报告逐项核对？",
                    "同日初检与复查是否分别匹配？",
                    "单位和参考范围差异是否已记录？",
                ],
            ),
            (
                "3. 安全事件、问题与后续",
                [
                    "异常检验是否按适用方案或IB规则进一步核实？",
                    "未解决问题是否进入下次监查遗留？",
                ],
            ),
        ],
    )
    build(
        "synthetic_monitoring_review_v2.docx",
        "合成中心监查报告核查模板 V2",
        [
            (
                "1. 知情同意",
                [
                    "知情同意版本是否为事件日适用版本？",
                    "签署人、日期和研究者确认是否完整？",
                ],
            ),
            (
                "2. 数据一致性",
                [
                    "检验报告与EDC导出范围是否一致？",
                    "原始结果、单位与参考范围是否保留来源？",
                ],
            ),
            (
                "3. 问题管理",
                [
                    "本次发现是否关联责任行动和报告章节？",
                    "遗留事项是否在下一次监查接续？",
                ],
            ),
        ],
    )


if __name__ == "__main__":
    main()
