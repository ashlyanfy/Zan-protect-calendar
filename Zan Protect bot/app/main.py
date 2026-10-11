import asyncio
import secrets
from contextlib import asynccontextmanager

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import Response

from app.cases import Case
from app.config import settings
from app.documents import build_draft, export
from app.knowledge import LegalMaterial, PublishRequest, SchemeMaterial, publish, put_material
from app.llm import Assistant
from app.schemas import AnalyzeRequest, ExportRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = settings()
    pool = await asyncpg.create_pool(cfg.database_url, min_size=1, max_size=5)
    app.state.assistant = Assistant(cfg, pool)
    app.state.pool = pool
    app.state.gate = asyncio.Semaphore(cfg.max_concurrent_requests)
    yield
    await app.state.assistant.client.close()
    await pool.close()


app = FastAPI(title="Zan Protect API", version="0.2.0", lifespan=lifespan)


def authorize(x_api_key: str = Header(default="")):
    if not secrets.compare_digest(x_api_key, settings().api_secret):
        raise HTTPException(401, "Unauthorized")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}


@app.get("/ready")
async def ready():
    try:
        await asyncio.wait_for(app.state.pool.fetchval("SELECT 1 FROM schema_migrations LIMIT 1"), 3)
        return {"status": "ready"}
    except Exception:  # noqa: BLE001 -- sanitized readiness boundary
        raise HTTPException(503, "Database unavailable") from None


@app.post("/v1/analyze", dependencies=[Depends(authorize)])
async def analyze(request: AnalyzeRequest):
    if app.state.gate.locked():
        raise HTTPException(429, "Capacity reached; retry later")
    async with app.state.gate:
        try:
            answer, sources = await asyncio.wait_for(app.state.assistant.analyze(
                request.text, request.mode, request.language, request.web_consent), timeout=180)
            return {"answer": answer, "sources": sources}
        except Exception:  # noqa: BLE001 -- sanitize all provider/database failures at API boundary
            raise HTTPException(503, "Analysis unavailable; no risk conclusion produced") from None


@app.post("/v1/documents", dependencies=[Depends(authorize)])
async def documents(request: ExportRequest):
    if sum(len(str(x)) for x in request.facts.values()) > 24000:
        raise HTTPException(422, "Too much text")
    if not request.confirmed:
        raise HTTPException(422, "User confirmation required")
    try:
        case = Case(branch=request.branch, facts=request.facts)
        case.confirm()
        return build_draft(request.kind, case, request.language)
    except ValueError:
        raise HTTPException(422, "Incomplete or invalid facts") from None


@app.post("/v1/documents/export", dependencies=[Depends(authorize)])
async def export_document(request: ExportRequest):
    if app.state.gate.locked():
        raise HTTPException(429, "Capacity reached; retry later")
    async with app.state.gate:
        draft = await documents(request)
        output = await asyncio.to_thread(export, draft, request.format, settings().font_path)
    types = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "txt": "text/plain; charset=utf-8"}
    return Response(output, media_type=types[request.format], headers={
        "Content-Disposition": f'attachment; filename="zan-{request.kind}.{request.format}"'})


def admin_authorize(x_admin_key: str = Header(default="")):
    secret = settings().admin_secret
    if len(secret) < 32 or not secrets.compare_digest(x_admin_key, secret):
        raise HTTPException(401, "Admin authorization required")


@app.post("/admin/legal", dependencies=[Depends(admin_authorize)])
async def add_legal(item: LegalMaterial):
    await put_material(app.state.pool, item, "api-admin")
    return {"id": item.id, "status": "draft"}


@app.post("/admin/schemes", dependencies=[Depends(admin_authorize)])
async def add_scheme(item: SchemeMaterial):
    await put_material(app.state.pool, item, "api-admin")
    return {"id": item.id, "status": "draft"}


@app.post("/admin/{kind}/{item_id}/publish", dependencies=[Depends(admin_authorize)])
async def publish_item(kind: str, item_id: str, request: PublishRequest):
    try:
        await publish(app.state.pool, kind, item_id, request)
    except ValueError:
        raise HTTPException(422, "Cannot publish missing or expired material") from None
    return {"id": item_id, "published": request.publish}


@app.get("/admin/status", dependencies=[Depends(admin_authorize)])
async def corpus_status():
    pool = app.state.pool
    return {"reviewed_schemes": await pool.fetchval("SELECT count(*) FROM scheme_cards WHERE status='reviewed'"),
            "approved_sources": await pool.fetchval("SELECT count(*) FROM legal_sources WHERE approved AND review_due>=current_date"),
            "queued_jobs": await pool.fetchval("SELECT count(*) FROM bot_jobs WHERE status='queued'"),
            "failed_jobs": await pool.fetchval("SELECT count(*) FROM bot_jobs WHERE status='failed'")}
