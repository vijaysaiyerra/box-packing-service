"""Application errors and handlers that format consistent API responses."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)


class APIError(Exception):
    """An error with the status and details to return to an API caller."""

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: list[dict[str, object]] | None = None,
    ) -> None:
        """Store the information used to build the error response."""
        self.status = status
        self.code = code
        self.message = message
        self.details = details or []
        super().__init__(message)


def error_response(
    status: int,
    code: str,
    message: str,
    details: list[dict[str, object]] | None = None,
) -> JSONResponse:
    """Build and log the standard JSON structure used for API errors."""
    content = {"error": {"code": code, "message": message, "details": details or []}}
    logger.info("Response sent: status=%d body=%s", status, content)
    return JSONResponse(
        status_code=status,
        content=content,
    )


async def handle_api_error(request: Request, error: APIError) -> JSONResponse:
    """Turn an APIError into its HTTP response."""
    logger.warning(
        "Request failed: %s %s returned %d (%s)",
        request.method,
        request.url.path,
        error.status,
        error.code,
    )
    return error_response(error.status, error.code, error.message, error.details)


async def handle_http_error(_: Request, error: HTTPException) -> JSONResponse:
    """Return HTTP errors using the standard error structure."""
    return error_response(error.status_code, "http_error", str(error.detail))


async def handle_validation_error(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    """Format request validation failures using the standard error structure."""
    details = [
        {
            "field": format_validation_field(problem["loc"][1:]),
            "message": problem["msg"],
        }
        for problem in error.errors()
    ]
    logger.warning(
        "Request validation failed: %s %s details=%s",
        request.method,
        request.url.path,
        details,
    )
    return error_response(422, "validation_error", "The request body is invalid.", details)


def format_validation_field(location: tuple[object, ...] | list[object]) -> str:
    """Format a validation location like [0].width for API clients."""
    field = ""
    for part in location:
        if isinstance(part, int):
            field += f"[{part}]"
        else:
            field += f".{part}" if field else str(part)
    return field or "body"


async def handle_unexpected_error(_: Request, error: Exception) -> JSONResponse:
    """Log unexpected failures and return a safe generic server error."""
    logger.error(
        "Unexpected error: %s",
        error,
        exc_info=(type(error), error, error.__traceback__),
    )
    return error_response(500, "internal_error", "Something went wrong on our side.")


def register_error_handlers(app: FastAPI) -> None:
    """Register handlers for application, HTTP, validation, and server errors."""
    app.add_exception_handler(APIError, handle_api_error)
    app.add_exception_handler(HTTPException, handle_http_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
