from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import openpyxl
from docx import Document
from PIL import Image
from reportlab.pdfgen import canvas

from medical_one_person.domain.knowledge import SourceSearchRequest
from medical_one_person.domain.knowledge.documents import IngestState
from medical_one_person.infrastructure.knowledge.contracts import KnowledgeContractValidator
from medical_one_person.infrastructure.knowledge.parsers import DocumentParser
from medical_one_person.infrastructure.sources import PubMedXmlAdapter, SourceRouter
from medical_one_person.infrastructure.sources.policies import load_source_policies


def _source_policy_path() -> Path:
    return Path(__file__).resolve().parents[4] / "config" / "source_policies" / "catalog.yaml"


def test_source_router_labels_pubmed_records_and_rejects_general_web() -> None:
    policies = load_source_policies(_source_policy_path())
    xml = b"""
    <PubmedArticleSet><PubmedArticle>
      <MedlineCitation>
        <PMID>12345</PMID>
        <Article>
          <ArticleTitle>Synthetic study title</ArticleTitle>
          <Abstract><AbstractText>Synthetic abstract.</AbstractText></Abstract>
          <Journal><Title>Synthetic Journal</Title></Journal>
          <ArticleDate><Year>2026</Year><Month>10</Month><Day>01</Day></ArticleDate>
          <PublicationTypeList><PublicationType>Preprint</PublicationType></PublicationTypeList>
        </Article>
      </MedlineCitation>
      <PubmedData><ArticleIdList>
        <ArticleId IdType="doi">10.0000/synthetic</ArticleId>
      </ArticleIdList></PubmedData>
    </PubmedArticle></PubmedArticleSet>
    """
    router = SourceRouter(policies, [PubMedXmlAdapter(xml)])
    request = SourceSearchRequest(
        query="synthetic",
        policy_id="biomedical_primary.v1",
    )

    records = router.search(request)

    assert len(records) == 1
    outcome = router.search_with_metadata(request)
    assert outcome.mode == "mock"
    assert outcome.adapter_ids == ("pubmed.xml.v1",)
    assert records[0].pmid == "12345"
    assert records[0].preprint is True
    assert records[0].peer_reviewed is False
    assert records[0].publication_date == date(2026, 10, 1)
    assert records[0].raw_fulltext_available is False
    assert policies["biomedical_primary.v1"].general_web_search is False


def test_all_knowledge_contract_examples_are_runtime_validated() -> None:
    root = Path(__file__).resolve().parents[4]
    validator = KnowledgeContractValidator(root / "schemas" / "knowledge.contracts.v1.schema.json")
    cases = json.loads(
        (root / "fixtures" / "knowledge-contract-examples.json").read_text(encoding="utf-8")
    )["cases"]

    for case in cases:
        assert validator.is_valid(case["contract"], case["data"]) is case["valid"], case["name"]


def test_document_parser_formats_and_locators(tmp_path) -> None:
    parser = DocumentParser()

    text_path = tmp_path / "notes.md"
    text_path.write_text("第一段\n内容\n\n第二段", encoding="utf-8")
    text = parser.parse(text_path, filename="notes.md", media_type="text/markdown")
    assert text.state == IngestState.READY
    assert text.passages[0].locator["start_line"] == 1
    assert text.passages[1].locator["start_line"] == 4

    csv_path = tmp_path / "table.csv"
    csv_path.write_text("name,value\na,1\nb,2\n", encoding="utf-8")
    csv_result = parser.parse(csv_path, filename="table.csv", media_type="text/csv")
    assert csv_result.tables[0].locator["table"] == 0
    assert csv_result.tables[0].data["rows"][1] == ["a", "1"]

    pdf_path = tmp_path / "paper.pdf"
    pdf = canvas.Canvas(str(pdf_path))
    pdf.drawString(72, 720, "Synthetic PDF evidence")
    pdf.showPage()
    pdf.save()
    pdf_result = parser.parse(pdf_path, filename="paper.pdf", media_type="application/pdf")
    assert pdf_result.passages[0].locator == {"page": 1}
    assert "Synthetic PDF evidence" in pdf_result.passages[0].text

    docx_path = tmp_path / "report.docx"
    document = Document()
    document.add_heading("Synthetic heading", level=1)
    document.add_paragraph("Synthetic paragraph")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "A"
    table.cell(0, 1).text = "B"
    document.save(docx_path)
    docx_result = parser.parse(
        docx_path,
        filename="report.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert any(item.locator["paragraph_index"] == 1 for item in docx_result.passages)
    assert docx_result.tables[0].locator == {"table": 0}

    xlsx_path = tmp_path / "workbook.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Synthetic"
    sheet["A1"] = "=1+1"
    sheet["A2"] = 3
    workbook.save(xlsx_path)
    xlsx_result = parser.parse(
        xlsx_path,
        filename="workbook.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert xlsx_result.tables[0].locator == {"sheet": "Synthetic"}
    assert xlsx_result.tables[0].data["cells"][0]["column"] == "A"

    image_path = tmp_path / "scan.png"
    Image.new("RGB", (32, 16), "white").save(image_path)
    image_result = parser.parse(image_path, filename="scan.png", media_type="image/png")
    assert image_result.state == IngestState.PARTIAL
    assert image_result.coverage["image"] == {"width": 32, "height": 16}
    assert image_result.quality_findings[0]["code"] == "OCR_UNAVAILABLE"

    eml_path = tmp_path / "message.eml"
    eml_path.write_text(
        "From: sender@example.com\n"
        "To: recipient@example.com\n"
        "Subject: Synthetic message\n"
        "Message-ID: <synthetic@example.com>\n"
        "Content-Type: text/plain; charset=utf-8\n\n"
        "Synthetic body\n",
        encoding="utf-8",
    )
    eml_result = parser.parse(eml_path, filename="message.eml", media_type="message/rfc822")
    assert eml_result.passages[0].locator == {"part": "body"}
