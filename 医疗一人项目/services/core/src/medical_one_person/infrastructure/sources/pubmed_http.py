from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Protocol
from urllib.parse import urlencode, urlsplit

from medical_one_person.domain.knowledge import SourceRecord, SourceSearchRequest
from medical_one_person.infrastructure.sources.adapters import (
    PubMedXmlAdapter,
    SourceExecutionMode,
)

OFFICIAL_PUBMED_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class SourceHttpTransport(Protocol):
    def __call__(
        self,
        url: str,
        headers: dict[str, str],
        timeout: float,
    ) -> tuple[int, bytes]: ...


class SourceRetrievalError(RuntimeError):
    pass


class SourceRetrievalRejected(SourceRetrievalError):
    pass


class SourceRetrievalRateLimited(SourceRetrievalError):
    pass


def urllib_source_transport(
    url: str,
    headers: dict[str, str],
    timeout: float,
) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except (OSError, TimeoutError) as exc:
        raise SourceRetrievalError("Scholarly source network request failed") from exc


class PubMedHttpAdapter:
    """NCBI E-utilities metadata adapter with injectable, offline-testable transport."""

    adapter_id = "pubmed.eutils.v1"
    policy_ids = frozenset({"biomedical_primary.v1"})

    def __init__(
        self,
        *,
        execution_mode: SourceExecutionMode,
        live_enabled: bool,
        base_url: str = OFFICIAL_PUBMED_EUTILS_BASE,
        tool_name: str,
        contact_email: str,
        api_key: str | None,
        timeout_seconds: float,
        max_results: int,
        transport: SourceHttpTransport = urllib_source_transport,
    ) -> None:
        parsed = urlsplit(base_url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "eutils.ncbi.nlm.nih.gov"
            or parsed.query
            or parsed.fragment
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError("PubMed adapter must use the official HTTPS E-utilities host")
        if not live_enabled:
            raise ValueError("PubMed live retrieval is not explicitly enabled")
        if not tool_name.strip() or "@" not in contact_email:
            raise ValueError("PubMed tool name and contact email are required")
        if timeout_seconds <= 0 or max_results <= 0:
            raise ValueError("PubMed timeout and result limit must be positive")
        self._base_url = base_url.rstrip("/")
        self._tool_name = tool_name.strip()
        self._contact_email = contact_email.strip()
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_results = max_results
        self._transport = transport
        self.mode = execution_mode

    def search(self, request: SourceSearchRequest) -> list[SourceRecord]:
        identifiers = self._search_identifiers(request)
        if not identifiers:
            return []
        xml = self._get(
            "/efetch.fcgi",
            {
                "db": "pubmed",
                "id": ",".join(identifiers),
                "retmode": "xml",
            },
        )
        return PubMedXmlAdapter(xml).search(request)

    def _search_identifiers(self, request: SourceSearchRequest) -> list[str]:
        params = {
            "db": "pubmed",
            "term": request.query,
            "retmode": "json",
            "retmax": str(self._max_results),
            "sort": "pub date",
        }
        if request.date_from is not None:
            params["mindate"] = request.date_from.isoformat()
            params["maxdate"] = (
                request.date_to.isoformat()
                if request.date_to is not None
                else request.date_from.isoformat()
            )
            params["datetype"] = "pdat"
        elif request.date_to is not None:
            raise SourceRetrievalRejected("date_to requires date_from")
        raw = self._get("/esearch.fcgi", params)
        try:
            body = json.loads(raw)
            identifiers = body["esearchresult"]["idlist"]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise SourceRetrievalError("PubMed ESearch returned invalid JSON") from exc
        if not isinstance(identifiers, list) or not all(
            isinstance(item, str) and item.isdigit() for item in identifiers
        ):
            raise SourceRetrievalError("PubMed ESearch returned invalid identifiers")
        return identifiers[: self._max_results]

    def _get(self, endpoint: str, params: dict[str, str]) -> bytes:
        query = {
            **params,
            "tool": self._tool_name,
            "email": self._contact_email,
        }
        if self._api_key:
            query["api_key"] = self._api_key
        url = self._base_url + endpoint + "?" + urlencode(query)
        status, raw = self._transport(
            url,
            {
                "Accept": "application/json, application/xml;q=0.9",
                "User-Agent": f"{self._tool_name}/1.0 ({self._contact_email})",
            },
            self._timeout_seconds,
        )
        if status == 429:
            raise SourceRetrievalRateLimited("PubMed E-utilities rate limit was reached")
        if status < 200 or status >= 300:
            raise SourceRetrievalError(f"PubMed E-utilities returned HTTP {status}")
        return raw
