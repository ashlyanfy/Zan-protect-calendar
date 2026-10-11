"""Import draft examples only. Publishing requires explicit editorial review in PostgreSQL."""
import asyncio
import json

import asyncpg

from app.config import ROOT, settings


async def main():
    conn = await asyncpg.connect(settings().database_url)
    try:
        cards = json.loads((ROOT / "data" / "schemes.seed.json").read_text(encoding="utf-8"))
        async with conn.transaction():
            for card in cards:
                await conn.execute("""
                    INSERT INTO scheme_cards(id,category,title_ru,title_kk,card,search_text)
                    VALUES($1,$2,$3,$4,$5::jsonb,$6) ON CONFLICT(id) DO NOTHING
                """, card["id"], card["category"], card["title_ru"], card["title_kk"],
                     json.dumps(card, ensure_ascii=False), json.dumps(card, ensure_ascii=False))
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
