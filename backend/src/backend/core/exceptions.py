from typing import Any


class AppError(Exception):
    status_code: int = 500
    error_type: str = "https://api.mycoai.dev/errors/internal"
    title: str = "Internal Server Error"

    def __init__(self, detail: str = "", **extra: Any) -> None:
        self.detail = detail
        self.extra = extra


class NotFoundError(AppError):
    status_code = 404
    error_type = "https://api.mycoai.dev/errors/not-found"
    title = "Resource Not Found"


class AuthenticationError(AppError):
    status_code = 401
    error_type = "https://api.mycoai.dev/errors/authentication"
    title = "Authentication Failed"


class AuthorizationError(AppError):
    status_code = 403
    error_type = "https://api.mycoai.dev/errors/authorization"
    title = "Forbidden"


class ValidationError(AppError):
    status_code = 400
    error_type = "https://api.mycoai.dev/errors/validation"
    title = "Validation Error"

    def __init__(
        self, detail: str = "", errors: list[dict[str, str]] | None = None
    ) -> None:
        super().__init__(detail)
        self.errors = errors or []


class ConflictError(AppError):
    status_code = 409
    error_type = "https://api.mycoai.dev/errors/conflict"
    title = "Conflict"
