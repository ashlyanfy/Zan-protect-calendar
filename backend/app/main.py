import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .routers import events

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ZanProtect Calendar API", version="1.0.0")

allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
