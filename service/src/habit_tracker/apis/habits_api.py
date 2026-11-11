# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from habit_tracker.apis.habits_api_base import BaseHabitsApi
import habit_tracker.impl

from fastapi import (  # noqa: F401
    APIRouter,
    Body,
    Cookie,
    Depends,
    Form,
    Header,
    HTTPException,
    Path,
    Query,
    Response,
    Security,
    status,
)

from pydantic import Field
from typing import Any, Optional
from typing_extensions import Annotated
from uuid import UUID
from habit_tracker.models.error import Error
from habit_tracker.models.frequency import Frequency
from habit_tracker.models.habit import Habit
from habit_tracker.models.habit_create import HabitCreate
from habit_tracker.models.habit_page import HabitPage
from habit_tracker.models.habit_update import HabitUpdate
from habit_tracker.models.status_filter import StatusFilter
from habit_tracker.models.extra_models import TokenModel  # noqa: F401
from habit_tracker.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = habit_tracker.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/habits",
    responses={
        200: {"model": HabitPage, "description": "Страница привычек."},
        400: {"model": Error, "description": "Запрос некорректен: неверный параметр, пустое или слишком длинное поле, пустое тело у PATCH. Исправьте запрос и повторите. "},
        401: {"model": Error, "description": "Сервис не знает, кто вы: заголовок Authorization отсутствует, токен просрочен или подпись неверна. Получите новый токен и повторите. "},
    },
    tags=["habits"],
    summary="Список привычек текущего пользователя",
    response_model_by_alias=True,
)
async def list_habits(
    status: Annotated[Optional[StatusFilter], Field(description="Какие привычки показывать.")] = Query('active', description="Какие привычки показывать.", alias="status"),
    frequency: Annotated[Optional[Frequency], Field(description="Фильтр по периодичности.")] = Query(None, description="Фильтр по периодичности.", alias="frequency"),
    limit: Annotated[Optional[Annotated[int, Field(le=100, ge=1)]], Field(description="Сколько записей вернуть.")] = Query(20, description="Сколько записей вернуть.", alias="limit", ge=1, le=100),
    offset: Annotated[Optional[Annotated[int, Field(ge=0)]], Field(description="Сколько записей пропустить с начала.")] = Query(0, description="Сколько записей пропустить с начала.", alias="offset", ge=0),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> HabitPage:
    """Возвращает страницу привычек. Чужие привычки в выдачу не попадают."""
    if not BaseHabitsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHabitsApi.subclasses[0]().list_habits(status, frequency, limit, offset)


@router.post(
    "/habits",
    responses={
        201: {"model": Habit, "description": "Привычка создана."},
        400: {"model": Error, "description": "Запрос некорректен: неверный параметр, пустое или слишком длинное поле, пустое тело у PATCH. Исправьте запрос и повторите. "},
        401: {"model": Error, "description": "Сервис не знает, кто вы: заголовок Authorization отсутствует, токен просрочен или подпись неверна. Получите новый токен и повторите. "},
        409: {"model": Error, "description": "Привычка с таким названием у вас уже есть."},
    },
    tags=["habits"],
    summary="Создать привычку",
    response_model_by_alias=True,
)
async def create_habit(
    habit_create: HabitCreate = Body(..., description="", examples=[{"title": "Пить воду", "description": "Два литра в день", "frequency": "DAILY", "targetPerPeriod": 1}]),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> Habit:
    """Создаёт привычку для текущего пользователя. Владелец берётся из токена, а не из тела запроса."""
    if not BaseHabitsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHabitsApi.subclasses[0]().create_habit(habit_create)


@router.get(
    "/habits/{habitId}",
    responses={
        200: {"model": Habit, "description": "Привычка найдена."},
        401: {"model": Error, "description": "Сервис не знает, кто вы: заголовок Authorization отсутствует, токен просрочен или подпись неверна. Получите новый токен и повторите. "},
        403: {"model": Error, "description": "Сервис знает, кто вы, но эта привычка принадлежит другому пользователю. Повторять запрос с тем же токеном бессмысленно. "},
        404: {"model": Error, "description": "Привычки с таким идентификатором нет."},
    },
    tags=["habits"],
    summary="Получить одну привычку",
    response_model_by_alias=True,
)
async def get_habit(
    habitId: Annotated[UUID, Field(description="Идентификатор привычки (UUID).")] = Path(..., description="Идентификатор привычки (UUID)."),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> Habit:
    if not BaseHabitsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHabitsApi.subclasses[0]().get_habit(habitId)


@router.delete(
    "/habits/{habitId}",
    responses={
        204: {"description": "Привычка удалена, тела ответа нет."},
        401: {"model": Error, "description": "Сервис не знает, кто вы: заголовок Authorization отсутствует, токен просрочен или подпись неверна. Получите новый токен и повторите. "},
        403: {"model": Error, "description": "Сервис знает, кто вы, но эта привычка принадлежит другому пользователю. Повторять запрос с тем же токеном бессмысленно. "},
        404: {"model": Error, "description": "Привычки с таким идентификатором нет."},
    },
    tags=["habits"],
    summary="Удалить привычку",
    response_model_by_alias=True,
)
async def delete_habit(
    habitId: Annotated[UUID, Field(description="Идентификатор привычки (UUID).")] = Path(..., description="Идентификатор привычки (UUID)."),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> None:
    """Удаляет привычку насовсем. Если нужно просто спрятать, лучше архивировать через PATCH."""
    if not BaseHabitsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHabitsApi.subclasses[0]().delete_habit(habitId)


@router.patch(
    "/habits/{habitId}",
    responses={
        200: {"model": Habit, "description": "Привычка изменена, в ответе её новое состояние."},
        400: {"model": Error, "description": "Запрос некорректен: неверный параметр, пустое или слишком длинное поле, пустое тело у PATCH. Исправьте запрос и повторите. "},
        401: {"model": Error, "description": "Сервис не знает, кто вы: заголовок Authorization отсутствует, токен просрочен или подпись неверна. Получите новый токен и повторите. "},
        403: {"model": Error, "description": "Сервис знает, кто вы, но эта привычка принадлежит другому пользователю. Повторять запрос с тем же токеном бессмысленно. "},
        404: {"model": Error, "description": "Привычки с таким идентификатором нет."},
    },
    tags=["habits"],
    summary="Частично изменить привычку",
    response_model_by_alias=True,
)
async def update_habit(
    habitId: Annotated[UUID, Field(description="Идентификатор привычки (UUID).")] = Path(..., description="Идентификатор привычки (UUID)."),
    habit_update: HabitUpdate = Body(..., description="", examples=[{"archived": True}]),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> Habit:
    """Меняет только переданные поля, остальные остаются как были. Чтобы отправить привычку в архив, передайте archived &#x3D; true. """
    if not BaseHabitsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHabitsApi.subclasses[0]().update_habit(habitId, habit_update)
