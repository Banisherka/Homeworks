"""Ошибки API в формате схемы Error из api.yaml (правлено руками)."""


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, headers: dict | None = None,
                 field_errors: list | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers
        self.field_errors = field_errors
