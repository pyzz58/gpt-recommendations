from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from typing import Protocol
from urllib.parse import urlparse

from medical_one_person.domain.knowledge import SourcePolicy, SourceRecord, SourceSearchRequest


class SourceAdapter(Protocol):
    @property
    def adapter_id(self) -> str: ...

    @property
    def policy_ids(self) -> frozenset[str]: ...

    def search(self, request: SourceSearchRequest) -> list[SourceRecord]: ...


class SourcePolicyViolation(ValueError):
    pass


class SourceUnavailableError(RuntimeError):
    pass


class PubMedXmlAdapter:
    """Parses cached PubMed XML; network fetching is intentionally separate."""

    adapter_id = "pubmed.xml.v1"
    policy_ids = frozenset({"biomedical_primary.v1"})

    def __init__(self, xml: bytes) -> None:
        self._xml = xml

    def search(self, request: SourceSearchRequest) -> list[SourceRecord]:
        root = ET.fromstring(self._xml)
        records: list[SourceRecord] = []
        for article in root.findall(".//PubmedArticle"):
            pmid = _text(article.find(".//PMID"))
            title = _text(article.find(".//ArticleTitle")) or "Untitled PubMed record"
            abstract_parts = [
                "".join(node.itertext()).strip() for node in article.findall(".//AbstractText")
            ]
            date_node = article.find(".//ArticleDate")
            if date_node is None:
                date_node = article.find(".//PubDate")
            publication_date = _parse_date(date_node)
            journal = _text(article.find(".//Journal/Title"))
            doi = next(
                (
                    _text(node)
                    for node in article.findall(".//ArticleId")
                    if node.attrib.get("IdType") == "doi"
                ),
                None,
            )
            publication_types = {_text(node) for node in article.findall(".//PublicationType")}
            peer_reviewed = "Preprint" not in publication_types
            records.append(
                SourceRecord(
                    source_id=pmid or doi or f"pubmed:{len(records)}",
                    title=title,
                    abstract="\n".join(part for part in abstract_parts if part) or None,
                    journal=journal,
                    publication_date=publication_date,
                    source_url=(
                        f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                        if pmid
                        else "https://pubmed.ncbi.nlm.nih.gov/"
                    ),
                    source_kind="bibliographic_database",
                    peer_reviewed=peer_reviewed,
                    preprint=not peer_reviewed,
                    retracted="Retracted Publication" in publication_types,
                    doi=doi,
                    pmid=pmid,
                    raw_fulltext_available=False,
                    limitations=[
                        "PubMed XML metadata does not establish fulltext access or study validity."
                    ],
                )
            )
        return records


class SourceRouter:
    def __init__(
        self,
        policies: dict[str, SourcePolicy],
        adapters: list[SourceAdapter],
    ) -> None:
        self._policies = policies
        self._adapters = adapters

    @property
    def available(self) -> bool:
        return bool(self._adapters)

    @property
    def adapter_ids(self) -> tuple[str, ...]:
        return tuple(sorted(adapter.adapter_id for adapter in self._adapters))

    @property
    def mode(self) -> str:
        return "live" if self._adapters else "mock"

    def search(self, request: SourceSearchRequest) -> list[SourceRecord]:
        if not self._adapters:
            raise SourceUnavailableError("No live scholarly source adapter is configured")
        policy = self._policies.get(request.policy_id)
        if policy is None:
            raise SourcePolicyViolation("Unknown source policy")
        if policy.general_web_search:
            raise SourcePolicyViolation("General web search must remain disabled")
        allowed_hosts = {channel.host for channel in policy.channels if channel.host is not None}
        results: list[SourceRecord] = []
        for adapter in self._adapters:
            if request.policy_id not in adapter.policy_ids:
                continue
            for record in adapter.search(request):
                host = urlparse(record.source_url).hostname
                if host is not None and host not in allowed_hosts:
                    raise SourcePolicyViolation(
                        f"Adapter returned a host outside the source policy: {host}"
                    )
                if record.preprint and policy.preprint_policy != "label_separately":
                    raise SourcePolicyViolation("Preprint is prohibited by the source policy")
                results.append(record)
        return results


def _text(node: ET.Element | None) -> str | None:
    if node is None:
        return None
    value = "".join(node.itertext()).strip()
    return value or None


def _parse_date(node: ET.Element | None) -> date | None:
    if node is None:
        return None
    year = _text(node.find("Year"))
    month = _text(node.find("Month"))
    day = _text(node.find("Day"))
    if not year or not year.isdigit():
        return None
    month_number = 1
    if month:
        if month.isdigit():
            month_number = int(month)
        else:
            month_names = {
                "Jan": 1,
                "Feb": 2,
                "Mar": 3,
                "Apr": 4,
                "May": 5,
                "Jun": 6,
                "Jul": 7,
                "Aug": 8,
                "Sep": 9,
                "Oct": 10,
                "Nov": 11,
                "Dec": 12,
            }
            month_number = month_names.get(month[:3], 1)
    try:
        return date(int(year), month_number, int(day) if day and day.isdigit() else 1)
    except ValueError:
        return None
