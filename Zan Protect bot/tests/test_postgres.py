import os
from datetime import date, timedelta
from urllib.parse import urlparse

import asyncpg
import pytest
from cryptography.fernet import Fernet

from app.knowledge import LegalMaterial, PublishRequest, content_hash, publish, put_material
from app.retrieval import retrieve
from app.storage import PrivateStore
from scripts.migrate import apply


@pytest.fixture
async def pool():
    url = os.environ.get("ZAN_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set ZAN_TEST_DATABASE_URL for isolated PostgreSQL integration tests")
    target = urlparse(url)
    if target.path != "/zan_test" or target.hostname not in {"localhost", "127.0.0.1", "host.docker.internal"}:
        raise RuntimeError("Integration tests only permit an isolated local zan_test database")
    pool = await asyncpg.create_pool(url, min_size=1, max_size=4)
    async with pool.acquire() as conn:
        await apply(conn)
        await apply(conn)
        await conn.execute("TRUNCATE private_sessions,bot_jobs,request_quotas,legal_sources,scheme_cards,knowledge_embeddings,editorial_audit")
    yield pool
    await pool.close()


async def test_database_queue_and_quota(pool):
    store = PrivateStore(pool, Fernet.generate_key().decode(), max_jobs=1)
    session = await store.get("test")
    session.history = ["private text"]
    await store.save("test", session)
    assert (await store.get("test")).history == ["private text"]
    assert b"private text" not in await pool.fetchval("SELECT payload FROM private_sessions WHERE id='test'")
    assert await store.quota("test", 2)
    assert await store.quota("test", 2)
    assert not await store.quota("test", 2)
    assert await store.enqueue(1, "test", {"text": "secret"})
    assert await store.enqueue(1, "test", {"text": "duplicate"})
    assert not await store.enqueue(2, "test", {})
    row = await store.claim()
    assert row["update_id"] == 1 and store.open(row["payload"])["text"] == "secret"
    assert await store.claim() is None
    await store.delete("test")
    assert not await store.active(1)
    assert await pool.fetchval("SELECT payload FROM bot_jobs WHERE update_id=1") is None


async def test_database_lease_recovery(pool):
    store = PrivateStore(pool, Fernet.generate_key().decode())
    await store.enqueue(10, "x", {})
    await store.claim()
    await pool.execute("UPDATE bot_jobs SET lease_until=now()-interval '1 second'")
    assert (await store.claim())["update_id"] == 10
    await store.finish(10, True)
    assert await pool.fetchval("SELECT payload FROM bot_jobs WHERE update_id=10") is None


async def test_database_publication_expiry_and_semantic_search(pool):
    today = date.today()
    source = LegalMaterial(id="test-law", title="Мошенничество обращение", url="https://www.gov.kz/test",
        language="ru", excerpt="Описание процедуры обращения в банк при мошенничестве. " * 2,
        checked_on=today, review_due=today+timedelta(days=5))
    await put_material(pool, source, "test-editor")
    assert not (await retrieve(pool, "мошенничество", today))[1]
    await publish(pool, "legal", source.id, PublishRequest(reviewer="Test lawyer"))
    assert (await retrieve(pool, "мошенничество", today))[1][0].id == source.id
    await pool.execute("INSERT INTO knowledge_embeddings VALUES('legal','test-law','test-model',2,$1,ARRAY[1,0]::real[])",
                       content_hash(source.title + "\n" + source.excerpt))
    assert (await retrieve(pool, "несовпадающее", today, [1.0,0.0], "test-model"))[1][0].id == source.id
    await pool.execute("UPDATE legal_sources SET review_due=$1", today-timedelta(days=1))
    assert not (await retrieve(pool, "мошенничество", today, [1.0,0.0], "test-model"))[1]
