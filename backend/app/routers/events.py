from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Event
from ..schemas import EventCreate, EventOut, EventUpdate

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=list[EventOut])
def list_events(
    start: datetime | None = Query(None, description="Фильтр: события с этой даты"),
    end: datetime | None = Query(None, description="Фильтр: события до этой даты"),
    db: Session = Depends(get_db),
):
    stmt = select(Event).order_by(Event.start_time)
    if start is not None:
        stmt = stmt.where(Event.start_time >= start)
    if end is not None:
        stmt = stmt.where(Event.start_time <= end)
    return db.scalars(stmt).all()


@router.post("", response_model=EventOut, status_code=201)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    event = Event(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: str, db: Session = Depends(get_db)):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    return event


@router.put("/{event_id}", response_model=EventOut)
def update_event(event_id: str, payload: EventUpdate, db: Session = Depends(get_db)):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    for key, value in payload.model_dump().items():
        setattr(event, key, value)
    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: str, db: Session = Depends(get_db)):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    db.delete(event)
    db.commit()
