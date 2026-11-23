from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class APIError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: list[dict[str, object]] | None = None,
    ) -> None:
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
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details or []}},
    )


async def handle_api_error(_: Request, error: APIError) -> JSONResponse:
    return error_response(error.status, error.code, error.message, error.details)


async def handle_validation_error(
    _: Request, error: RequestValidationError
) -> JSONResponse:
    details = [
        {
            "field": ".".join(map(str, problem["loc"][1:])) or "body",
            "message": problem["msg"],
        }
        for problem in error.errors()
    ]
    return error_response(422, "validation_error", "The request body is invalid.", details)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(APIError, handle_api_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
