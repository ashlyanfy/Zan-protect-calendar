"""Apply ordered SQL migrations once, atomically, serialized across Railway services."""
import asyncio
import hashlib
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
LOCK_ID = 8182459001


async def apply(conn, directory: Path = SQL_DIR):
    async with conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock($1)", LOCK_ID)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name text PRIMARY KEY,
                checksum text NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
        """)
        for path in sorted(directory.glob("[0-9]*.sql")):
            # Normalize CRLF so a Windows checkout and Linux image yield the same checksum.
            sql = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
            previous = await conn.fetchval("SELECT checksum FROM schema_migrations WHERE name=$1", path.name)
            if previous is not None:
                if previous != checksum:
                    raise RuntimeError(f"Applied migration changed: {path.name}; create a new migration")
                continue
            await conn.execute(sql)
            await conn.execute("INSERT INTO schema_migrations(name,checksum) VALUES($1,$2)",
                               path.name, checksum)


async def migrate_database(database_url: str):
    conn = await asyncpg.connect(database_url, timeout=30, command_timeout=120)
    try:
        await apply(conn)
        print("Database migrations completed", flush=True)
    finally:
        await conn.close()


async def main():
    load_dotenv(SQL_DIR.parent / ".env")
    await migrate_database(os.environ["DATABASE_URL"])


if __name__ == "__main__":
    asyncio.run(main())
