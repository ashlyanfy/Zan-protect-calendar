import json
import re
from datetime import date

from app.knowledge import content_hash, cosine, fuse
from app.schemas import Source


def query_terms(text: str) -> str:
    words = re.findall(r"[a-zа-яёәіңғүұқөһ]{3,}", text.lower())
    return " | ".join(dict.fromkeys(words[:80]))


async def retrieve(pool, text: str, today: date, vector=None, model: str = "") -> tuple[list[dict], list[Source]]:
    query = query_terms(text)
    if not query:
        return [], []
    async with pool.acquire() as conn:
        cards = await conn.fetch("""
            SELECT id,card FROM scheme_cards, to_tsquery('simple', $1) q
            WHERE status='reviewed' AND search_vector @@ q
            ORDER BY ts_rank(search_vector,q) DESC LIMIT 20
        """, query)
        sources = await conn.fetch("""
            SELECT id,title,url,excerpt,checked_on FROM legal_sources, to_tsquery('simple',$1) q
            WHERE approved AND review_due >= $2 AND checked_on <= $2
            AND (effective_from IS NULL OR effective_from <= $2)
            AND (effective_to IS NULL OR effective_to >= $2)
            AND search_vector @@ q ORDER BY ts_rank(search_vector,q) DESC LIMIT 20
        """, query, today)
        lawyer = await conn.fetch("""
            SELECT id::text AS id,title,content,created_at::date AS checked_on FROM lawyer_materials, to_tsquery('simple',$1) q
            WHERE active AND search_vector @@ q ORDER BY ts_rank(search_vector,q) DESC LIMIT 10
        """, query)
        if vector:
            candidates = await conn.fetch("""
                SELECT e.*,s.card,NULL::text AS title,NULL::text AS url,NULL::text AS excerpt,NULL::date AS checked_on,s.search_text AS current_text
                FROM knowledge_embeddings e JOIN scheme_cards s ON e.kind='scheme' AND e.item_id=s.id
                WHERE s.status='reviewed' AND e.model=$1 AND e.dimensions=$2
                UNION ALL
                SELECT e.*,NULL::jsonb,l.title,l.url,l.excerpt,l.checked_on,l.title||E'\n'||l.excerpt AS current_text
                FROM knowledge_embeddings e JOIN legal_sources l ON e.kind='legal' AND e.item_id=l.id
                WHERE l.approved AND l.checked_on<=$3 AND l.review_due>=$3
                AND (l.effective_from IS NULL OR l.effective_from<=$3)
                AND (l.effective_to IS NULL OR l.effective_to>=$3) AND e.model=$1 AND e.dimensions=$2
                UNION ALL
                SELECT e.*,NULL::jsonb,m.title,NULL::text,NULL::text,m.created_at::date,m.title||E'\n'||m.content AS current_text
                FROM knowledge_embeddings e JOIN lawyer_materials m ON e.kind='lawyer' AND e.item_id=m.id::text
                WHERE m.active AND e.model=$1 AND e.dimensions=$2
                LIMIT 5000
            """, model, len(vector), today)
            semantic = sorted(((cosine(vector, r["embedding"]), r) for r in candidates
                               if content_hash(r["current_text"]) == r["content_hash"]),
                              key=lambda pair: pair[0], reverse=True)
            for kind in ["scheme", "legal", "lawyer"]:
                ranked = [r for score, r in semantic if score >= 0.25 and r["kind"] == kind][:20]
                lexical = {"scheme": cards, "legal": sources, "lawyer": lawyer}[kind]
                lookup = {r["id"]: dict(r) for r in lexical}
                for row in ranked:
                    if kind == "scheme":
                        lookup[row["item_id"]] = {"id": row["item_id"], "card": row["card"]}
                    elif kind == "legal":
                        lookup[row["item_id"]] = {"id": row["item_id"], **{k: row[k] for k in ["title", "url", "excerpt", "checked_on"]}}
                    else:
                        lookup[row["item_id"]] = {"id": row["item_id"], "title": row["title"],
                                                  "content": row["current_text"].split("\n", 1)[1],
                                                  "checked_on": row["checked_on"]}
                merged = [lookup[key] for key in fuse([r["id"] for r in lexical], [r["item_id"] for r in ranked])]
                if kind == "scheme":
                    cards = merged
                elif kind == "legal":
                    sources = merged
                else:
                    lawyer = merged
    lawyer_sources = [Source(id="lawyer-" + row["id"], title=row["title"], url="Внутренний материал юриста Zan Protect",
                             checked_on=row["checked_on"].isoformat(), excerpt=row["content"][:6000])
                      for row in lawyer[:2]]
    legal_sources = [Source(**{**dict(row), "checked_on": row["checked_on"].isoformat()})
                     for row in sources[:6 - len(lawyer_sources)]]
    return ([json.loads(row["card"]) if isinstance(row["card"], str) else row["card"] for row in cards[:5]],
            legal_sources + lawyer_sources)
