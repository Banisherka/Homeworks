"""Логика сервиса в памяти (правлено руками; генератор создаёт только абстрактный класс).

Внутренняя запись HabitRow хранит поля, которых нет в API (owner_id, row_version, deleted_at).
В ответ они не попадают: _to_dto собирает Habit только из полей схемы.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from pydantic import ConfigDict

from habit_tracker.apis.habits_api_base import BaseHabitsApi
from habit_tracker.errors import ApiError
from habit_tracker.models.frequency import Frequency
from habit_tracker.models.habit import Habit
from habit_tracker.models.habit_create import HabitCreate
from habit_tracker.models.habit_page import HabitPage
from habit_tracker.models.habit_update import HabitUpdate
from habit_tracker.models.status_filter import StatusFilter
from habit_tracker.security_api import current_user_id


@dataclass
class HabitRow:
    id: UUID
    owner_id: str                      # внутреннее: наружу не едет
    title: str
    frequency: Frequency
    target_per_period: int
    description: Optional[str] = None
    archived: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    row_version: int = 1               # внутреннее: наружу не едет
    deleted_at: Optional[datetime] = None  # внутреннее: наружу не едет


DB: Dict[UUID, HabitRow] = {}

# В спеке у HabitCreate и HabitUpdate стоит additionalProperties: false, а сгенерированные модели
# лишние поля молча отбрасывают. Включаем запрет здесь, а не в models/: этот файл при
# регенерации не перезаписывается (impl/ в .openapi-generator-ignore).
for _model in (HabitCreate, HabitUpdate):
    _model.model_config = ConfigDict(**{**_model.model_config, "extra": "forbid"})
    _model.model_rebuild(force=True)


def _to_dto(row: HabitRow) -> Habit:
    return Habit(id=row.id, title=row.title, description=row.description, frequency=row.frequency,
                 target_per_period=row.target_per_period, archived=row.archived,
                 current_streak=0,  # серию считали бы по отметкам; в этих 5 эндпоинтах отметок нет
                 created_at=row.created_at)


def _own(habit_id: UUID) -> HabitRow:
    row = DB.get(habit_id)
    if row is None:
        raise ApiError(404, "habit_not_found", "Привычка не найдена")
    if row.owner_id != current_user_id.get():
        raise ApiError(403, "forbidden", "Эта привычка вам не принадлежит")
    return row


class HabitsApiImpl(BaseHabitsApi):
    async def list_habits(self, status, frequency, limit, offset) -> HabitPage:
        me = current_user_id.get()
        rows = sorted((r for r in DB.values() if r.owner_id == me), key=lambda r: r.created_at)
        status = status or StatusFilter.ACTIVE
        if status == StatusFilter.ACTIVE:
            rows = [r for r in rows if not r.archived]
        elif status == StatusFilter.ARCHIVED:
            rows = [r for r in rows if r.archived]
        if frequency is not None:
            rows = [r for r in rows if r.frequency == frequency]
        page = rows[offset:offset + limit]
        return HabitPage(items=[_to_dto(r) for r in page], total=len(rows), limit=limit, offset=offset)

    async def create_habit(self, habit_create: HabitCreate):
        me = current_user_id.get()
        if any(r.owner_id == me and r.title.casefold() == habit_create.title.casefold() for r in DB.values()):
            raise ApiError(409, "habit_already_exists", "Привычка с таким названием уже есть")
        row = HabitRow(id=uuid.uuid4(), owner_id=me, title=habit_create.title,
                       description=habit_create.description, frequency=habit_create.frequency,
                       target_per_period=habit_create.target_per_period or 1)
        DB[row.id] = row
        # генератор не ставит код успеха, поэтому 201 и Location отдаём сами
        return JSONResponse(status_code=201, content=jsonable_encoder(_to_dto(row), by_alias=True),
                            headers={"Location": f"/api/v1/habits/{row.id}"})

    async def get_habit(self, habitId: UUID) -> Habit:
        return _to_dto(_own(habitId))

    async def update_habit(self, habitId: UUID, habit_update: HabitUpdate) -> Habit:
        row = _own(habitId)
        changes = habit_update.model_dump(exclude_unset=True)
        if not changes:
            raise ApiError(400, "validation_failed", "Нужно передать хотя бы одно поле")
        for name, value in changes.items():
            setattr(row, name, value)
        row.row_version += 1
        return _to_dto(row)

    async def delete_habit(self, habitId: UUID):
        row = _own(habitId)
        del DB[row.id]
        return Response(status_code=204)   # то же: генератор оставляет 200
