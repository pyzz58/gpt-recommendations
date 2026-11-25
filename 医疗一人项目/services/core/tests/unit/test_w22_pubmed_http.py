from __future__ import annotations

from datetime import date
from urllib.parse import parse_qs, urlparse

import pytest

from medical_one_person.config import Settings
from medical_one_person.domain.knowledge import SourceSearchRequest
from medical_one_person.domain.recovery import NetworkMode
from medical_one_person.infrastructure.sources.factory import build_source_adapters
from medical_one_person.infrastructure.sources.pubmed_http import (
    PubMedHttpAdapter,
    SourceRetrievalError,
    SourceRetrievalRateLimited,
)

PUBMED_XML = b"""
<PubmedArticleSet><PubmedArticle>
  <MedlineCitation>
    <PMID>98765</PMID>
    <Article>
      <ArticleTitle>Offline E-utilities record</ArticleTitle>
      <Abstract><AbstractText>Synthetic abstract only.</AbstractText></Abstract>
      <Journal><Title>Synthetic Journal</Title></Journal>
      <ArticleDate><Year>2026</Year><Month>11</Month><Day>01</Day></ArticleDate>
      <PublicationTypeList><PublicationType>Journal Article</PublicationType></PublicationTypeList>
    </Article>
  </MedlineCitation>
  <PubmedData><ArticleIdList>
    <ArticleId IdType="doi">10.0000/offline</ArticleId>
  </ArticleIdList></PubmedData>
</PubmedArticle></PubmedArticleSet>
"""


def adapter(transport) -> PubMedHttpAdapter:
    return PubMedHttpAdapter(
        execution_mode="mock",
        live_enabled=True,
        tool_name="medical-one-test",
        contact_email="owner@example.test",
        api_key="test-key-not-real",
        timeout_seconds=2,
        max_results=10,
        transport=transport,
    )


def request() -> SourceSearchRequest:
    return SourceSearchRequest(
        query="synthetic feline drug",
        policy_id="biomedical_primary.v1",
        date_from=date(2025, 1, 1),
        date_to=date(2026, 11, 1),
    )


def test_pubmed_esearch_efetch_contract_is_offline() -> None:
    calls = []

    def transport(url, headers, timeout):
        calls.append((url, headers, timeout))
        if "/esearch.fcgi" in url:
            return 200, b'{"esearchresult":{"idlist":["98765"]}}'
        return 200, PUBMED_XML

    records = adapter(transport).search(request())

    assert len(records) == 1
    assert records[0].pmid == "98765"
    assert records[0].doi == "10.0000/offline"
    assert records[0].publication_date == date(2026, 11, 1)
    assert records[0].peer_reviewed is True
    assert records[0].raw_fulltext_available is False
    assert len(calls) == 2
    search_query = parse_qs(urlparse(calls[0][0]).query)
    assert search_query["term"] == ["synthetic feline drug"]
    assert search_query["mindate"] == ["2025-01-01"]
    assert search_query["maxdate"] == ["2026-11-01"]
    assert search_query["tool"] == ["medical-one-test"]
    assert search_query["email"] == ["owner@example.test"]
    assert search_query["api_key"] == ["test-key-not-real"]
    assert parse_qs(urlparse(calls[1][0]).query)["id"] == ["98765"]


def test_pubmed_factory_requires_live_flag_allowlisted_network_and_identity() -> None:
    base = {
        "source_pubmed_live_enabled": True,
        "source_pubmed_tool": "medical-one-test",
        "source_pubmed_email": "owner@example.test",
    }

    assert build_source_adapters(Settings(**base)) == []
    assert build_source_adapters(
        Settings(
            **{**base, "source_pubmed_live_enabled": False},
            network_mode=NetworkMode.ALLOWLISTED,
        )
    ) == []
    live = build_source_adapters(
        Settings(
            **base,
            network_mode=NetworkMode.ALLOWLISTED,
        )
    )
    assert len(live) == 1
    assert live[0].adapter_id == "pubmed.eutils.v1"
    assert live[0].mode == "live"


def test_pubmed_rate_limit_and_invalid_identifier_are_explicit() -> None:
    with pytest.raises(SourceRetrievalRateLimited):
        adapter(lambda url, headers, timeout: (429, b"")).search(request())

    with pytest.raises(SourceRetrievalError, match="invalid identifiers"):
        adapter(
            lambda url, headers, timeout: (
                200,
                b'{"esearchresult":{"idlist":["not-an-id"]}}',
            )
        ).search(request())


def test_pubmed_adapter_rejects_non_official_host() -> None:
    with pytest.raises(ValueError, match="official HTTPS"):
        PubMedHttpAdapter(
            execution_mode="live",
            live_enabled=True,
            base_url="https://example.com/entrez/eutils",
            tool_name="medical-one-test",
            contact_email="owner@example.test",
            api_key=None,
            timeout_seconds=2,
            max_results=10,
            transport=lambda url, headers, timeout: (200, b""),
        )
