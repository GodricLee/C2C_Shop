"""Custom exception management for the C2C backend."""
from __future__ import annotations

from typing import Any, Dict, NoReturn

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Application-specific error that translates into JSON responses."""

    def __init__(self, status_code: int, message: str, detail: Dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.detail = detail

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"message": self.message}
        if self.detail is not None:
            payload["detail"] = self.detail
        return payload


def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    """Convert AppError instances to JSON responses."""

    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


def register_app_error_handler(app: FastAPI) -> None:
    """Register AppError handler on the FastAPI application."""

    app.add_exception_handler(AppError, handle_app_error)  # type: ignore[arg-type]


def raise_app_error(status_code: int, message: str, detail: Dict[str, Any] | None = None) -> NoReturn:
    """Helper to raise an AppError with consistent signature."""

    raise AppError(status_code=status_code, message=message, detail=detail)
