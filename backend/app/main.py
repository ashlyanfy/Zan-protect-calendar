import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from sqlalchemy import inspect, select, text

from .database import Base, SessionLocal, engine
from .models import User
from .routers import auth, events, users
from .security import hash_password

Base.metadata.create_all(bind=engine)


def _migrate_and_seed():
    # Мини-миграция: добавляем колонки в существующую таблицу events (create_all их не добавит)
    inspector = inspect(engine)
    existing = {c["name"] for c in inspector.get_columns("events")}
    with engine.begin() as conn:
        if "owner_id" not in existing:
            conn.execute(text("ALTER TABLE events ADD COLUMN owner_id VARCHAR(36)"))
        if "is_shared" not in existing:
            conn.execute(text("ALTER TABLE events ADD COLUMN is_shared BOOLEAN NOT NULL DEFAULT FALSE"))

    # Первый запуск: заводим аккаунты из env SEED_USERS (прод) или backend/seed_users.json (локально).
    # Файл в .gitignore — пароли не попадают в репозиторий. Существующие логины не трогаем.
    import json

    seed_raw = os.getenv("SEED_USERS")
    if not seed_raw:
        seed_file = Path(__file__).resolve().parent.parent / "seed_users.json"
        seed_raw = seed_file.read_text(encoding="utf-8") if seed_file.is_file() else None

    with SessionLocal() as db:
        if seed_raw:
            for entry in json.loads(seed_raw):
                login = entry["login"].strip().lower()
                if db.scalar(select(User).where(User.login == login)) is None:
                    db.add(
                        User(
                            login=login,
                            password_hash=hash_password(entry["password"]),
                            name=entry["name"],
                            role=entry.get("role", "employee"),
                        )
                    )
            db.commit()

        admin = db.scalar(select(User).where(User.role == "admin"))
        if admin is None:
            admin = User(
                login=os.getenv("ADMIN_LOGIN", "admin").strip().lower(),
                password_hash=hash_password(os.getenv("ADMIN_PASSWORD", "zanprotect2026")),
                name=os.getenv("ADMIN_NAME", "Администратор"),
                role="admin",
            )
            db.add(admin)
            db.flush()
        # события, созданные до ввода аккаунтов, отдаём администратору
        db.execute(text("UPDATE events SET owner_id = :oid WHERE owner_id IS NULL"), {"oid": admin.id})
        db.commit()


_migrate_and_seed()

app = FastAPI(title="ZanProtect Calendar API", version="1.0.0")

allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(events.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# В проде (Railway) FastAPI раздаёт собранный фронтенд из frontend/dist
_app_dir = Path(__file__).resolve().parent
_candidates = [
    _app_dir.parent / "frontend" / "dist",          # Docker: /app/frontend/dist
    _app_dir.parent.parent / "frontend" / "dist",   # локально: <repo>/frontend/dist
]
static_dir = next((p for p in _candidates if p.is_dir()), _candidates[0])
if static_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        # resolve() + is_relative_to закрывают выход из dist через "../"
        file = (static_dir / full_path).resolve()
        if full_path and file.is_file() and file.is_relative_to(static_dir.resolve()):
            return FileResponse(file)
        return FileResponse(static_dir / "index.html")
