from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 400
    default_detail = "Application error"
    headers: dict[str, str] | None = None

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    default_detail = "Not found"


class ConflictError(AppError):
    status_code = 409
    default_detail = "Conflict"


class BusinessRuleError(AppError):
    status_code = 422
    default_detail = "Business rule violation"


class UnauthorizedError(AppError):
    status_code = 401
    default_detail = "Could not validate credentials"
    headers = {"WWW-Authenticate": "Bearer"}


class ForbiddenError(AppError):
    status_code = 403
    default_detail = "Forbidden"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )