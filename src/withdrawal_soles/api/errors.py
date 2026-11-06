"""Map domain and validation errors to the public error envelope."""

import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from withdrawal_soles.domain.exceptions import DomainError

logger = logging.getLogger(__name__)


def install_error_handlers(app: FastAPI) -> None:
    """Attach the shared error handlers to the application."""

    @app.exception_handler(DomainError)
    async def domain_error_handler(
        _request: Request, error: DomainError
    ) -> JSONResponse:
        headers = (
            {"WWW-Authenticate": "Bearer"}
            if error.status_code == 401
            else None
        )
        return JSONResponse(
            status_code=error.status_code,
            headers=headers,
            content={
                "code": error.code,
                "message": error.message,
                "details": error.details,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "The request does not match the API contract.",
                "details": {"errors": jsonable_encoder(error.errors())},
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        _request: Request, error: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled application error", exc_info=error)
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "The service could not complete the request.",
                "details": {},
            },
        )
