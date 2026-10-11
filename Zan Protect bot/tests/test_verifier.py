from unittest.mock import AsyncMock

from app.schemas import Answer, Claim
from app.verification import Review, safe_fallback, verify


def answer():
    return Answer(language="ru", risk="high", summary="x", evidence=[], explanation="x",
                  immediate_actions=[], next_actions=[], questions=[], legal_claims=[], uncertainty="", lawyer_needed=False)


async def test_unsupported_claim_falls_back():
    assistant = AsyncMock()
    reject = Review(approved=False, unsupported_claims=["promise"], reason="unsupported")
    assistant.structured.side_effect = [reject, answer(), reject]
    result = await verify(assistant, answer(), [], "facts")
    assert result.risk == "unknown" and result.lawyer_needed and not result.legal_claims
    assert [x.args[0] for x in assistant.structured.await_args_list] == ["verify", "repair", "verify"]


async def test_web_summary_not_used_as_law():
    assistant = AsyncMock()
    draft = answer()
    draft.legal_claims = [Claim(text="legal promise", source_ids=["web-1"])]
    assistant.structured.side_effect = [answer(), Review(approved=True, unsupported_claims=[], reason="ok")]
    result = await verify(assistant, draft, [], "facts")
    assert not result.legal_claims
    assert assistant.structured.await_args_list[0].args[0] == "repair"


async def test_repaired_answer_must_pass_review():
    assistant = AsyncMock()
    corrected = answer()
    corrected.summary = "Сохраните переписку с угрозами."
    assistant.structured.side_effect = [Review(approved=False, unsupported_claims=[], reason="repair style"),
                                       corrected, Review(approved=True, unsupported_claims=[], reason="ok")]
    result = await verify(assistant, answer(), [], "Мне угрожают", "blackmail")
    assert result.summary == corrected.summary


async def test_unverified_repair_never_reaches_user():
    assistant = AsyncMock()
    bad = answer()
    bad.legal_claims = [Claim(text="Invented law", source_ids=["nonexistent"])]
    assistant.structured.side_effect = [Review(approved=False, unsupported_claims=["bad"], reason="bad"), bad]
    result = await verify(assistant, answer(), [], "Угроза публикации фото", "blackmail")
    assert not result.legal_claims
    assert result.risk == "high"
    assert not any("банк" in text.lower() for text in result.immediate_actions)


async def test_review_timeout_returns_relevant_safety_steps():
    assistant = AsyncMock()
    assistant.structured.side_effect = TimeoutError()
    result = await verify(assistant, answer(), [], "Угроза публикации фото", "blackmail")
    assert result.questions and result.risk == "high"


def test_generic_fallback_does_not_assume_financial_threat():
    result = safe_fallback("ru")
    assert "банк" not in str(result.model_dump()).lower()
