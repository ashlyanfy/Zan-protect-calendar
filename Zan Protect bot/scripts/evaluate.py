"""Explicit live LLM evaluation. Uses synthetic/redacted JSONL; never uploads private corpora by default."""
import argparse
import asyncio
import json
from pathlib import Path

import asyncpg

from app.config import settings
from app.llm import Assistant


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--output", type=Path, default=Path("test-results/eval.json"))
    args = parser.parse_args()
    cases = [json.loads(x) for x in args.file.read_text(encoding="utf-8").splitlines() if x.strip()]
    cfg = settings()
    pool = await asyncpg.create_pool(cfg.database_url, min_size=1, max_size=3)
    assistant = Assistant(cfg, pool)
    results = []
    try:
        for case in cases:
            try:
                answer, sources = await assistant.analyze(case["text"], case["mode"], case["language"], web=False)
                passed = answer.risk in case["allowed_risks"] and answer.language == case["language"]
                results.append({"id": case["id"], "passed": passed, "risk": answer.risk, "sources": len(sources)})
            except Exception as exc:  # noqa: BLE001 -- record type only, never private input
                results.append({"id": case["id"], "passed": False, "error": type(exc).__name__})
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"model": cfg.openai_model, "results": results}, indent=2), encoding="utf-8")
        print(f"Passed {sum(r['passed'] for r in results)}/{len(results)}; human legal review still required")
    finally:
        await assistant.client.close()
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
