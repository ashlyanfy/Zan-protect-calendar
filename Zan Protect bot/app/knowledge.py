import hashlib
import math
from datetime import date
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, model_validator

from app.schemas import StrictModel


class LegalMaterial(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9_-]{3,100}$")
    title: str = Field(min_length=5, max_length=300)
    url: str = Field(max_length=2000)
    language: Literal["ru", "kk"]
    excerpt: str = Field(min_length=60, max_length=12000)
    checked_on: date
    review_due: date
    effective_from: date | None = None
    effective_to: date | None = None

    @model_validator(mode="after")
    def valid_source(self):
        p = urlparse(self.url)
        domains = ["adilet.zan.kz", "gov.kz", "egov.kz", "nationalbank.kz"]
        if p.scheme != "https" or p.username or not any(p.hostname == d or (p.hostname or "").endswith("."+d) for d in domains):
            raise ValueError("Official HTTPS source required")
        if self.review_due < self.checked_on:
            raise ValueError("Invalid review dates")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("Invalid effective dates")
        return self


class SchemeMaterial(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9_-]{3,100}$")
    category: Literal["impersonation", "relative_emergency", "dropper_recruitment", "p2p_dirty_transfer",
                      "investment", "marketplace", "account_takeover", "phishing", "fraudulent_loan",
                      "romance_extortion", "fake_benefit", "fake_lottery"]
    title_ru: str = Field(min_length=5, max_length=200)
    title_kk: str = Field(min_length=5, max_length=200)
    risk: Literal["high", "medium", "low", "unknown"]
    signs: list[str] = Field(min_length=1, max_length=50)
    steps: list[str] = Field(min_length=1, max_length=20)
    victim_risks: list[str] = Field(min_length=1, max_length=20)
    aftercare: list[str] = Field(min_length=1, max_length=20)
    participant_liability: str | None = None
    legal_source_ids: list[str] = Field(default_factory=list, max_length=30)
    variations_ru: list[str] = Field(min_length=1, max_length=30)
    variations_kk: list[str] = Field(min_length=1, max_length=30)
    synthetic: bool
    provenance: str = Field(min_length=10, max_length=2000)


class PublishRequest(StrictModel):
    reviewer: str = Field(min_length=3, max_length=100)
    publish: bool = True


async def put_material(pool, item, actor: str):
    kind = "legal" if isinstance(item, LegalMaterial) else "scheme"
    async with pool.acquire() as conn, conn.transaction():
        if kind == "legal":
            await conn.execute("""
                INSERT INTO legal_sources(id,title,url,language,excerpt,checked_on,review_due,effective_from,effective_to)
                VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)
                ON CONFLICT(id) DO UPDATE SET title=excluded.title,url=excluded.url,language=excluded.language,
                  excerpt=excluded.excerpt,checked_on=excluded.checked_on,review_due=excluded.review_due,
                  effective_from=excluded.effective_from,effective_to=excluded.effective_to,approved=false,approved_by=NULL
            """, item.id, item.title, item.url, item.language, item.excerpt, item.checked_on,
                 item.review_due, item.effective_from, item.effective_to)
        else:
            body = item.model_dump_json()
            await conn.execute("""
                INSERT INTO scheme_cards(id,category,title_ru,title_kk,card,search_text) VALUES($1,$2,$3,$4,$5::jsonb,$5)
                ON CONFLICT(id) DO UPDATE SET category=excluded.category,title_ru=excluded.title_ru,
                  title_kk=excluded.title_kk,card=excluded.card,search_text=excluded.search_text,
                  status='draft',reviewed_by=NULL,reviewed_at=NULL
            """, item.id, item.category, item.title_ru, item.title_kk, body)
        await conn.execute("DELETE FROM knowledge_embeddings WHERE kind=$1 AND item_id=$2", kind, item.id)
        await conn.execute("INSERT INTO editorial_audit(kind,item_id,action,actor) VALUES($1,$2,'draft_updated',$3)", kind, item.id, actor)


async def publish(pool, kind: str, item_id: str, request: PublishRequest):
    async with pool.acquire() as conn, conn.transaction():
        if kind == "legal":
            result = await conn.execute("""
                UPDATE legal_sources SET approved=$2,approved_by=$3 WHERE id=$1
                AND (NOT $2 OR (checked_on<=current_date AND review_due>=current_date))
            """, item_id, request.publish, request.reviewer)
        elif kind == "scheme":
            result = await conn.execute("""
                UPDATE scheme_cards SET status=$2,reviewed_by=$3,reviewed_at=now() WHERE id=$1
            """, item_id, "reviewed" if request.publish else "retired", request.reviewer)
        else:
            raise ValueError("Unknown knowledge kind")
        if result == "UPDATE 0":
            raise ValueError("Missing material or expired review")
        await conn.execute("INSERT INTO editorial_audit(kind,item_id,action,actor) VALUES($1,$2,$3,$4)",
                           kind, item_id, "publish" if request.publish else "withdraw", request.reviewer)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    denominator = math.sqrt(sum(x*x for x in a) * sum(x*x for x in b))
    return sum(x*y for x, y in zip(a, b, strict=True)) / denominator if denominator else 0.0


def fuse(*rankings: list[str]) -> list[str]:
    scores = {}
    for ranking in rankings:
        for rank, key in enumerate(dict.fromkeys(ranking), 1):
            scores[key] = scores.get(key, 0) + 1 / (60 + rank)
    return sorted(scores, key=lambda key: (-scores[key], key))


async def index_knowledge(pool, client, config) -> int:
    rows = await pool.fetch("""
        SELECT 'scheme' AS kind,id AS item_id,search_text AS text FROM scheme_cards WHERE status='reviewed'
        UNION ALL SELECT 'legal',id,title||E'\n'||excerpt FROM legal_sources WHERE approved
    """)
    updated = 0
    for row in rows:
        text = row["text"]
        digest = content_hash(text)
        exists = await pool.fetchval("""
            SELECT 1 FROM knowledge_embeddings WHERE kind=$1 AND item_id=$2 AND content_hash=$3 AND model=$4 AND dimensions=$5
        """, row["kind"], row["item_id"], digest, config.embedding_model, config.embedding_dimensions)
        if exists:
            continue
        response = await client.embeddings.create(model=config.embedding_model, dimensions=config.embedding_dimensions,
                                                  input=text, encoding_format="float")
        vector = response.data[0].embedding
        await pool.execute("""
            INSERT INTO knowledge_embeddings(kind,item_id,model,dimensions,content_hash,embedding) VALUES($1,$2,$3,$4,$5,$6)
            ON CONFLICT(kind,item_id) DO UPDATE SET model=excluded.model,dimensions=excluded.dimensions,
                content_hash=excluded.content_hash,embedding=excluded.embedding
        """, row["kind"], row["item_id"], config.embedding_model, config.embedding_dimensions, digest, vector)
        updated += 1
    return updated
