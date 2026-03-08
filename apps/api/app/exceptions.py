from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger


class DomainError(Exception):
    """Base domain exception."""

    def __init__(self, detail: str, status_code: int = 500, error_type: str = "error"):
        self.detail = detail
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(detail)


class ServiceUnavailableError(DomainError):
    def __init__(self, detail: str = "Service unavailable"):
        super().__init__(detail, status_code=503, error_type="service_unavailable")


class HealthCheckError(DomainError):
    def __init__(self, detail: str = "Health check failed"):
        super().__init__(detail, status_code=503, error_type="health_check_error")


class DocumentNotFoundError(DomainError):
    def __init__(self, document_id: str):
        super().__init__(
            detail=f"No document found with id: {document_id}",
            status_code=404,
            error_type="document_not_found",
        )


class InvalidFileTypeError(DomainError):
    def __init__(self, detail: str):
        super().__init__(
            detail=detail,
            status_code=422,
            error_type="invalid_file_type",
        )


class DocumentNotReadyError(DomainError):
    def __init__(self, document_id: str, status: str):
        super().__init__(
            detail=f"Document {document_id} is not ready for text retrieval (status: {status})",
            status_code=409,
            error_type="document_not_ready",
        )


class DocumentProcessingError(DomainError):
    def __init__(self, document_id: str, detail: str):
        super().__init__(
            detail=f"Document processing failed for {document_id}: {detail}",
            status_code=422,
            error_type="document_processing_failed",
        )


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": f"urn:osint:error:{exc.error_type}",
            "title": exc.error_type.replace("_", " ").title(),
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url.path),
        },
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on {path}", path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "type": "urn:osint:error:internal",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred",
            "instance": str(request.url.path),
        },
    )
