from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EventType = Literal["court", "meeting", "deadline", "consultation", "other"]


class EventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=5000)
    event_type: EventType = "other"
    location: str | None = Field(None, max_length=300)
    case_number: str | None = Field(None, max_length=100)
    start_time: datetime
    end_time: datetime | None = None
    reminder_minutes: int | None = Field(None, ge=0, le=20160)  # до 14 дней

    @field_validator("title", "location", "case_number")
    @classmethod
    def strip_text(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("title")
    @classmethod
    def title_required(cls, v: str | None) -> str:
        if not v:
            raise ValueError("Название события обязательно")
        return v

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, v: datetime | None, info) -> datetime | None:
        start = info.data.get("start_time")
        if v is not None and start is not None:
            v_cmp = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
            s_cmp = start if start.tzinfo else start.replace(tzinfo=timezone.utc)
            if v_cmp <= s_cmp:
                raise ValueError("Время окончания должно быть позже начала")
        return v


class EventCreate(EventBase):
    pass


class EventUpdate(EventBase):
    pass


class EventOut(EventBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime

    # SQLite отдаёт naive UTC — помечаем зону явно, чтобы клиент показывал локальное время
    @field_validator("start_time", "end_time", "created_at", "updated_at")
    @classmethod
    def ensure_utc(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
