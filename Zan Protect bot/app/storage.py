"""Encrypted TTL state and bounded durable Telegram inbox on PostgreSQL."""
import json
import time
from dataclasses import asdict
from datetime import UTC, datetime

from cryptography.fernet import Fernet

from app.privacy import Session


class PrivateStore:
    def __init__(self, pool, encryption_key: str, ttl: int = 1800, max_jobs: int = 200):
        self.pool = pool
        self.cipher = Fernet(encryption_key.encode())
        self.ttl, self.max_jobs = ttl, max_jobs

    def seal(self, value) -> bytes:
        return self.cipher.encrypt(json.dumps(value, ensure_ascii=False).encode())

    def open(self, value: bytes):
        return json.loads(self.cipher.decrypt(value))

    async def get(self, key: str) -> Session:
        row = await self.pool.fetchrow("SELECT payload,expires_at FROM private_sessions WHERE id=$1 AND expires_at>now()", key)
        if not row:
            return Session(expires=time.time() + self.ttl)
        data = self.open(row["payload"])
        data["expires"] = row["expires_at"].timestamp()
        data["busy"] = False
        return Session(**data)

    async def save(self, key: str, session: Session):
        if session.expires <= time.time():
            await self.delete(key)
            return
        await self.pool.execute("""
            INSERT INTO private_sessions(id,payload,expires_at) VALUES($1,$2,$3)
            ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,expires_at=excluded.expires_at
        """, key, self.seal(asdict(session)), datetime.fromtimestamp(session.expires, UTC))

    async def delete(self, key: str):
        async with self.pool.acquire() as conn, conn.transaction():
            await conn.execute("DELETE FROM private_sessions WHERE id=$1", key)
            await conn.execute("UPDATE bot_jobs SET status='cancelled',payload=NULL WHERE session_id=$1", key)

    async def quota(self, key: str, limit: int) -> bool:
        count = await self.pool.fetchval("""
            INSERT INTO request_quotas(id,day,requests) VALUES($1,(now() AT TIME ZONE 'Asia/Qyzylorda')::date,1)
            ON CONFLICT(id,day) DO UPDATE SET requests=request_quotas.requests+1
            WHERE request_quotas.requests<$2 RETURNING requests
        """, key, limit)
        return count is not None

    async def enqueue(self, update_id: int, key: str, payload: dict) -> bool:
        async with self.pool.acquire() as conn, conn.transaction():
            # Serialize capacity check + insertion, without retaining raw request text in logs.
            await conn.execute("SELECT pg_advisory_xact_lock(8182459002)")
            if await conn.fetchval("SELECT 1 FROM bot_jobs WHERE update_id=$1", update_id):
                return True
            count = await conn.fetchval("SELECT count(*) FROM bot_jobs WHERE status IN ('queued','running') AND expires_at>now()")
            per_user = await conn.fetchval("SELECT count(*) FROM bot_jobs WHERE session_id=$1 AND status IN ('queued','running') AND expires_at>now()", key)
            if count >= self.max_jobs or per_user >= 5:
                return False
            await conn.execute("""
                INSERT INTO bot_jobs(update_id,session_id,payload,expires_at)
                VALUES($1,$2,$3,now()+$4*interval '1 second')
            """, update_id, key, self.seal(payload), self.ttl)
            return True

    async def claim(self):
        async with self.pool.acquire() as conn, conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(8182459002)")
            await conn.execute("""
                UPDATE bot_jobs SET status=CASE WHEN attempts<2 THEN 'queued' ELSE 'failed' END,
                    payload=CASE WHEN attempts<2 THEN payload ELSE NULL END
                WHERE status='running' AND lease_until<now()
            """)
            row = await conn.fetchrow("""
                SELECT * FROM bot_jobs j WHERE status='queued' AND expires_at>now()
                AND NOT EXISTS(SELECT 1 FROM bot_jobs r WHERE r.session_id=j.session_id AND r.status='running')
                ORDER BY update_id LIMIT 1 FOR UPDATE SKIP LOCKED
            """)
            if not row:
                return None
            await conn.execute("UPDATE bot_jobs SET status='running',attempts=attempts+1,lease_until=now()+interval '240 seconds' WHERE update_id=$1", row["update_id"])
            return row

    async def active(self, update_id: int) -> bool:
        return bool(await self.pool.fetchval("SELECT 1 FROM bot_jobs WHERE update_id=$1 AND status='running' AND expires_at>now()", update_id))

    async def finish(self, update_id: int, success: bool):
        await self.pool.execute("UPDATE bot_jobs SET status=$2,payload=NULL,lease_until=NULL WHERE update_id=$1 AND status='running'", update_id, "done" if success else "failed")

    async def purge(self):
        await self.pool.execute("DELETE FROM private_sessions WHERE expires_at<=now()")
        await self.pool.execute("DELETE FROM bot_jobs WHERE expires_at<=now()")
        await self.pool.execute("DELETE FROM request_quotas WHERE day<(now() AT TIME ZONE 'Asia/Qyzylorda')::date")
