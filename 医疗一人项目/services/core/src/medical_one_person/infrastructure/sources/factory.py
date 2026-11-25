from __future__ import annotations

from medical_one_person.config import Settings
from medical_one_person.domain.recovery import NetworkMode
from medical_one_person.infrastructure.sources.adapters import SourceAdapter
from medical_one_person.infrastructure.sources.pubmed_http import (
    OFFICIAL_PUBMED_EUTILS_BASE,
    PubMedHttpAdapter,
)


def build_source_adapters(settings: Settings) -> list[SourceAdapter]:
    if (
        not settings.source_pubmed_live_enabled
        or settings.network_mode != NetworkMode.ALLOWLISTED
        or not settings.source_pubmed_tool
        or not settings.source_pubmed_email
    ):
        return []
    return [
        PubMedHttpAdapter(
            execution_mode="live",
            live_enabled=True,
            base_url=settings.source_pubmed_base_url or OFFICIAL_PUBMED_EUTILS_BASE,
            tool_name=settings.source_pubmed_tool,
            contact_email=settings.source_pubmed_email,
            api_key=settings.source_pubmed_api_key,
            timeout_seconds=settings.source_pubmed_timeout_seconds,
            max_results=settings.source_pubmed_max_results,
        )
    ]
