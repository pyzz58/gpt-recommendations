from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from medical_one_person.application.project_views import WorkspaceReader
from medical_one_person.application.sessions import AuthenticatedPrincipal
from medical_one_person.domain.knowledge import SourceRecord, SourceSearchRequest
from medical_one_person.infrastructure.sources.adapters import (
    SourcePolicyViolation,
    SourceRouter,
    SourceUnavailableError,
)
from medical_one_person.infrastructure.sources.pubmed_http import (
    SourceRetrievalError,
    SourceRetrievalRateLimited,
)


def build_source_search_router(
    *,
    source_router: SourceRouter,
    project_reader: WorkspaceReader,
    current_principal: Callable[[Request], AuthenticatedPrincipal],
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/projects/{project_id}/sources",
        tags=["sources"],
    )

    @router.post(
        "/search",
        response_model=list[SourceRecord],
        responses={
            400: {"description": "Unknown or prohibited source policy"},
            429: {"description": "Upstream scholarly source rate limit"},
            502: {"description": "Upstream scholarly source retrieval failure"},
            503: {"description": "No live scholarly source adapter configured"},
        },
    )
    def search_sources(
        project_id: UUID,
        request: SourceSearchRequest,
        principal: AuthenticatedPrincipal = Depends(current_principal),
    ) -> list[SourceRecord]:
        project_reader.get_project(
            actor_user_id=principal.user_id,
            project_id=project_id,
        )
        try:
            return source_router.search(request)
        except SourceUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "SOURCE_ADAPTER_UNAVAILABLE",
                    "message": str(exc),
                },
            ) from exc
        except SourcePolicyViolation as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "SOURCE_POLICY_REJECTED",
                    "message": str(exc),
                },
            ) from exc
        except SourceRetrievalRateLimited as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "SOURCE_RATE_LIMITED",
                    "message": str(exc),
                },
            ) from exc
        except SourceRetrievalError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "SOURCE_RETRIEVAL_FAILED",
                    "message": str(exc),
                },
            ) from exc

    return router
