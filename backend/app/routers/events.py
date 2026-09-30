from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Event, User
from ..schemas import EventCreate, EventOut, EventUpdate
from ..security import get_current_user

router = APIRouter(prefix="/api/events", tags=["events"])


def _to_out(event: Event) -> EventOut:
    out = EventOut.model_validate(event)
    out.owner_name = event.owner.name if event.owner else None
    return out


def _resolve_target(user_id: str | None, user: User, db: Session) -> User:
    """Чей календарь смотрим. Чужой доступен только администратору."""
    if user_id is None or user_id == user.id:
        return user
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Доступно только администратору")
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    return target


def _get_visible_event(event_id: str, user: User, db: Session) -> Event:
    event = db.get(Event, event_id, options=[joinedload(Event.owner)])
    if event is None:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    if user.role != "admin" and not event.is_shared and event.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    return event


def _check_can_edit(event: Event, user: User):
    if user.role != "admin" and event.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Изменять может только автор события или администратор")


@router.get("", response_model=list[EventOut])
def list_events(
    start: datetime | None = Query(None, description="Фильтр: события с этой даты"),
    end: datetime | None = Query(None, description="Фильтр: события до этой даты"),
    user_id: str | None = Query(None, description="Чей календарь показать (только для админа)"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    target = _resolve_target(user_id, user, db)
    stmt = (
        select(Event)
        .options(joinedload(Event.owner))
        .where(or_(Event.owner_id == target.id, Event.is_shared.is_(True)))
        .order_by(Event.start_time)
    )
    if start is not None:
        stmt = stmt.where(Event.start_time >= start)
    if end is not None:
        stmt = stmt.where(Event.start_time <= end)
    return [_to_out(e) for e in db.scalars(stmt).all()]


@router.post("", response_model=EventOut, status_code=201)
def create_event(
    payload: EventCreate,
    user_id: str | None = Query(None, description="Создать событие для сотрудника (только для админа)"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    target = _resolve_target(user_id, user, db)
    event = Event(**payload.model_dump(), owner_id=target.id)
    db.add(event)
    db.commit()
    db.refresh(event)
    return _to_out(event)


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _to_out(_get_visible_event(event_id, user, db))


@router.put("/{event_id}", response_model=EventOut)
def update_event(
    event_id: str, payload: EventUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    event = _get_visible_event(event_id, user, db)
    _check_can_edit(event, user)
    for key, value in payload.model_dump().items():
        setattr(event, key, value)
    db.commit()
    db.refresh(event)
    return _to_out(event)


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    event = _get_visible_event(event_id, user, db)
    _check_can_edit(event, user)
    db.delete(event)
    db.commit()
