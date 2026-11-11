# coding: utf-8
"""Проверка JWT (правлено руками: в сгенерированном файле тут была заглушка '...').

401 = «не знаю, кто ты»: токена нет, он просрочен или подпись неверна.
Кто именно пришёл, кладём в ContextVar: сгенерированные маршруты не передают токен в impl.
"""
import contextvars
import os

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from habit_tracker.errors import ApiError
from habit_tracker.models.extra_models import TokenModel

bearer_auth = HTTPBearer(auto_error=False)   # ошибку 401 в нужном формате отдаём сами

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")   # для демо; в проде секрет из окружения
current_user_id: contextvars.ContextVar[str] = contextvars.ContextVar("current_user_id")


def _unauthorized() -> ApiError:
    return ApiError(401, "unauthorized", "Нужен действующий токен", headers={"WWW-Authenticate": "Bearer"})


async def get_token_bearerAuth(credentials: HTTPAuthorizationCredentials = Depends(bearer_auth)) -> TokenModel:
    if credentials is None:
        raise _unauthorized()
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise _unauthorized()
    sub = payload.get("sub")
    if not sub:
        raise _unauthorized()
    current_user_id.set(str(sub))
    return TokenModel(sub=str(sub))
