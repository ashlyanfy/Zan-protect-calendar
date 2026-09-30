from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import CredentialsUpdate, LoginRequest, TokenResponse, UserOut
from ..security import create_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.login == payload.login.strip().lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    return TokenResponse(token=create_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/credentials", response_model=TokenResponse)
def update_credentials(
    payload: CredentialsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Сотрудник сам меняет логин, имя и пароль — вход дальше по новым данным."""
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")

    if payload.login is not None:
        new_login = payload.login.lower()
        if new_login != user.login:
            if db.scalar(select(User).where(User.login == new_login)) is not None:
                raise HTTPException(status_code=409, detail="Такой логин уже занят")
            user.login = new_login
    if payload.name is not None:
        user.name = payload.name
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)

    db.commit()
    db.refresh(user)
    # токен подписан id пользователя, но после смены пароля выдаём новый
    return TokenResponse(token=create_token(user.id), user=UserOut.model_validate(user))
