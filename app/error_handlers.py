"""Custom error handlers and exceptions for the application."""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError
import traceback
from typing import Union

from .logging_config import get_logger

logger = get_logger("error_handlers")


class AppException(Exception):
    """Base exception for application-specific errors."""

    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ResourceNotFoundError(AppException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, identifier: Union[int, str]):
        super().__init__(
            message=f"{resource} with identifier '{identifier}' not found",
            status_code=404,
            details={"resource": resource, "identifier": str(identifier)}
        )


class DuplicateResourceError(AppException):
    """Raised when attempting to create a duplicate resource."""

    def __init__(self, resource: str, field: str, value: str):
        super().__init__(
            message=f"{resource} with {field} '{value}' already exists",
            status_code=409,
            details={"resource": resource, "field": field, "value": value}
        )


class ValidationError(AppException):
    """Raised when data validation fails."""

    def __init__(self, message: str, errors: list = None):
        super().__init__(
            message=message,
            status_code=422,
            details={"validation_errors": errors or []}
        )


class OCRError(AppException):
    """Raised when OCR processing fails."""

    def __init__(self, message: str, original_error: str = None):
        super().__init__(
            message=f"OCR processing failed: {message}",
            status_code=500,
            details={"original_error": original_error}
        )


async def app_exception_handler(request: Request, exc: AppException):
    """Handler for custom application exceptions."""
    logger.error(
        f"Application error: {exc.message}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details,
            "path": request.url.path
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler for request validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(
        f"Validation error on {request.method} {request.url.path}",
        extra={"validation_errors": errors}
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation failed",
            "validation_errors": errors,
            "path": request.url.path
        }
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handler for SQLAlchemy database errors."""
    error_msg = "Database error occurred"

    if isinstance(exc, IntegrityError):
        error_msg = "Data integrity constraint violated"
        status_code = status.HTTP_409_CONFLICT
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    logger.error(
        f"Database error: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__
        },
        exc_info=True
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": error_msg,
            "detail": str(exc.orig) if hasattr(exc, 'orig') else str(exc),
            "path": request.url.path
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handler for unexpected exceptions."""
    logger.critical(
        f"Unhandled exception: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc()
        },
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please contact support if the issue persists.",
            "path": request.url.path,
            "request_id": id(request)  # Simple request ID for tracking
        }
    )
