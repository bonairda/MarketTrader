"""Errores de dominio y manejo centralizado de excepciones para la API.

Objetivo: respuestas de error consistentes ({ "error": {...} }) y que ninguna
excepción inesperada filtre trazas al cliente.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

log = get_logger("errors")


class AppError(Exception):
    """Error de dominio con código y estado HTTP asociados."""

    def __init__(self, message: str, *, code: str = "APP_ERROR", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str = "Recurso no encontrado", *, code: str = "NOT_FOUND"):
        super().__init__(message, code=code, status_code=404)


def _error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Se registra la traza completa en el servidor, pero al cliente solo le
        # llega un mensaje genérico (no filtramos detalles internos).
        log.exception("[ERROR] Excepción no controlada en %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content=_error_body("INTERNAL_ERROR", "Error interno del servidor"),
        )
