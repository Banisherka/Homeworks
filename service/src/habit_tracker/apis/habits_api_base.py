# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

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
from habit_tracker.security_api import get_token_bearerAuth

class BaseHabitsApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseHabitsApi.subclasses = BaseHabitsApi.subclasses + (cls,)
    async def list_habits(
        self,
        status: Annotated[Optional[StatusFilter], Field(description="Какие привычки показывать.")],
        frequency: Annotated[Optional[Frequency], Field(description="Фильтр по периодичности.")],
        limit: Annotated[Optional[Annotated[int, Field(le=100, ge=1)]], Field(description="Сколько записей вернуть.")],
        offset: Annotated[Optional[Annotated[int, Field(ge=0)]], Field(description="Сколько записей пропустить с начала.")],
    ) -> HabitPage:
        """Возвращает страницу привычек. Чужие привычки в выдачу не попадают."""
        ...


    async def create_habit(
        self,
        habit_create: HabitCreate,
    ) -> Habit:
        """Создаёт привычку для текущего пользователя. Владелец берётся из токена, а не из тела запроса."""
        ...


    async def get_habit(
        self,
        habitId: Annotated[UUID, Field(description="Идентификатор привычки (UUID).")],
    ) -> Habit:
        ...


    async def delete_habit(
        self,
        habitId: Annotated[UUID, Field(description="Идентификатор привычки (UUID).")],
    ) -> None:
        """Удаляет привычку насовсем. Если нужно просто спрятать, лучше архивировать через PATCH."""
        ...


    async def update_habit(
        self,
        habitId: Annotated[UUID, Field(description="Идентификатор привычки (UUID).")],
        habit_update: HabitUpdate,
    ) -> Habit:
        """Меняет только переданные поля, остальные остаются как были. Чтобы отправить привычку в архив, передайте archived &#x3D; true. """
        ...
