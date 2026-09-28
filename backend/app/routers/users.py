from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import UserCreate, UserOut
from ..security import hash_password, require_admin

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.scalars(select(User).order_by(User.created_at)).all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    login = payload.login.strip().lower()
    if db.scalar(select(User).where(User.login == login)) is not None:
        raise HTTPException(status_code=409, detail="Такой логин уже занят")
    user = User(
        login=login,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role="employee",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить собственный аккаунт")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    db.delete(user)
    db.commit()
