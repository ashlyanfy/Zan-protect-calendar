"""Validate/import JSON knowledge without publishing it; index only reviewed material."""
import argparse
import asyncio
import json
from pathlib import Path

import asyncpg
from openai import AsyncOpenAI

from app.config import settings
from app.knowledge import LegalMaterial, SchemeMaterial, index_knowledge, put_material


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["validate", "import", "index"])
    parser.add_argument("--kind", choices=["legal", "scheme"])
    parser.add_argument("--file", type=Path)
    args = parser.parse_args()
    items = []
    if args.action != "index":
        if not args.kind or not args.file:
            parser.error("--kind and --file required")
        cls = LegalMaterial if args.kind == "legal" else SchemeMaterial
        items = [cls.model_validate(item) for item in json.loads(args.file.read_text(encoding="utf-8"))]
        print(f"Validated {len(items)} records")
        if args.action == "validate":
            return
    cfg = settings()
    pool = await asyncpg.create_pool(cfg.database_url, min_size=1, max_size=3)
    try:
        if args.action == "import":
            for item in items:
                await put_material(pool, item, "local-import")
            print("Imported as drafts; editorial publication required")
        else:
            async with AsyncOpenAI(api_key=cfg.openai_api_key) as client:
                print(f"Indexed {await index_knowledge(pool, client, cfg)} records")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
