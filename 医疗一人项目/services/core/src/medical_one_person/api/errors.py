from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from medical_one_person.application.errors import (
    ApplicationError,
    ConflictingOperationError,
    IdempotencyConflictError,
    NotFoundError,
    PlanStateError,
    ReviewPolicyError,
    RevisionConflictError,
    TaskNotReadyError,
)
from medical_one_person.application.exports import ExportRuntimeUnavailable
from medical_one_person.application.mail import MailAuthorizationError
from medical_one_person.infrastructure.knowledge.upload import KnowledgeUploadError
from medical_one_person.infrastructure.tables import TableImportError


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found(_request: Request, exc: NotFoundError) -> JSONResponse:
        return _response(status.HTTP_404_NOT_FOUND, "NOT_FOUND", str(exc), False)

    @app.exception_handler(PermissionError)
    async def forbidden(_request: Request, exc: PermissionError) -> JSONResponse:
        return _response(status.HTTP_403_FORBIDDEN, "NOT_AUTHORIZED", str(exc), False)

    @app.exception_handler(MailAuthorizationError)
    async def mail_authorization_error(
        _request: Request,
        exc: MailAuthorizationError,
    ) -> JSONResponse:
        return _response(
            status.HTTP_403_FORBIDDEN,
            "MAIL_AUTHORIZATION_DENIED",
            str(exc),
            False,
        )

    @app.exception_handler(RevisionConflictError)
    @app.exception_handler(ConflictingOperationError)
    @app.exception_handler(IdempotencyConflictError)
    async def conflict(_request: Request, exc: ApplicationError) -> JSONResponse:
        return _response(status.HTTP_409_CONFLICT, "VERSION_CONFLICT", str(exc), False)

    @app.exception_handler(TaskNotReadyError)
    @app.exception_handler(PlanStateError)
    async def task_not_ready(_request: Request, exc: TaskNotReadyError) -> JSONResponse:
        return _response(status.HTTP_409_CONFLICT, "INPUT_STALE", str(exc), False)

    @app.exception_handler(ReviewPolicyError)
    async def review_policy(_request: Request, exc: ReviewPolicyError) -> JSONResponse:
        return _response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "VALIDATION_FAILED",
            str(exc),
            False,
        )

    @app.exception_handler(ExportRuntimeUnavailable)
    async def export_runtime_unavailable(
        _request: Request,
        exc: ExportRuntimeUnavailable,
    ) -> JSONResponse:
        return _response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "EXPORT_RUNTIME_UNAVAILABLE",
            str(exc),
            True,
        )

    @app.exception_handler(TableImportError)
    async def table_import_error(_request: Request, exc: TableImportError) -> JSONResponse:
        status_code = (
            status.HTTP_413_CONTENT_TOO_LARGE
            if exc.code == "DATASET_TOO_LARGE"
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        return _response(status_code, exc.code, str(exc), False)

    @app.exception_handler(KnowledgeUploadError)
    async def upload_error(_request: Request, exc: KnowledgeUploadError) -> JSONResponse:
        status_code = status.HTTP_400_BAD_REQUEST
        if exc.code in {"DOCUMENT_RESTRICTED"}:
            status_code = status.HTTP_404_NOT_FOUND
        elif exc.code in {"UPLOAD_TOO_LARGE"}:
            status_code = status.HTTP_413_CONTENT_TOO_LARGE
        elif exc.code in {"UNSUPPORTED_FORMAT"}:
            status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        elif exc.code in {"CHECKSUM_MISMATCH"}:
            status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        elif exc.code in {"INCOMPLETE_UPLOAD", "VERSION_CONFLICT"}:
            status_code = status.HTTP_409_CONFLICT
        return _response(status_code, exc.code, str(exc), False)

    @app.exception_handler(ValueError)
    async def validation_error(_request: Request, exc: ValueError) -> JSONResponse:
        return _response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "VALIDATION_FAILED",
            str(exc),
            False,
        )


def _response(
    status_code: int,
    code: str,
    message: str,
    retryable: bool,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "retryable": retryable,
            "details": {},
        },
    )
