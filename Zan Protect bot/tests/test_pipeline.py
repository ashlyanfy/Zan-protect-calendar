from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.config import Settings, settings
from app.llm import TOPICS, Assistant
from app.main import authorize
from app.schemas import Answer, Intake


@pytest.fixture
def config():
    return Settings(_env_file=None, api_secret="a" * 32, session_secret="b" * 32,
                    openai_api_key="fake-local-test", enable_web_search=True,
                    enable_semantic_search=False, verify_answers=False)


async def test_research_query_never_uses_case_text(config):
    assistant = Assistant(config, None)
    create = AsyncMock(return_value=SimpleNamespace(output=[]))
    assistant.client.responses.create = create
    try:
        await assistant.research("fraud_loan", "2026-10-11")
        assert create.call_args.kwargs["input"] == TOPICS["fraud_loan"]
        assert create.call_args.kwargs["store"] is False
        assert create.call_args.kwargs["tools"][0]["filters"]["allowed_domains"]
    finally:
        await assistant.client.close()


async def test_pipeline_without_sources_does_not_invent_law(config, monkeypatch):
    assistant = Assistant(config, None)
    first = Intake(language="kk", situation="dropper", summary="Аударым қабылдау",
                   indicators=["комиссия"], risk_floor="high", search_topic="dropper", questions=[])
    answer = Answer(language="kk", risk="low", summary="Тәуекел", evidence=[], explanation="x",
                    immediate_actions=[], next_actions=[], questions=[], legal_claims=[],
                    uncertainty="Дереккөз жоқ", lawyer_needed=True)
    assistant.structured = AsyncMock(side_effect=[first, answer])
    assistant.research = AsyncMock(return_value=[])
    monkeypatch.setattr("app.llm.retrieve", AsyncMock(return_value=([], [])))
    try:
        result, sources = await assistant.analyze("Аударым қабылдау", "check", "kk", web=False)
        assert result.risk == "high" and not sources
        assistant.research.assert_not_awaited()
    finally:
        await assistant.client.close()


def test_api_rejects_missing_or_wrong_secret(monkeypatch):
    monkeypatch.setenv("API_SECRET", "a" * 32)
    monkeypatch.setenv("SESSION_SECRET", "b" * 32)
    settings.cache_clear()
    try:
        for secret in ["", "wrong"]:
            with pytest.raises(HTTPException) as exc:
                authorize(secret)
            assert exc.value.status_code == 401
        assert authorize("a" * 32) is None
    finally:
        settings.cache_clear()
