from unittest.mock import AsyncMock

from app.schemas import Answer, Claim
from app.verification import Review, verify


def answer():
    return Answer(language="ru", risk="high", summary="x", evidence=[], explanation="x",
                  immediate_actions=[], next_actions=[], questions=[], legal_claims=[], uncertainty="", lawyer_needed=False)


async def test_unsupported_claim_falls_back():
    assistant = AsyncMock()
    assistant.structured.return_value = Review(approved=False, unsupported_claims=["promise"], reason="unsupported")
    result = await verify(assistant, answer(), [], "facts")
    assert result.risk == "unknown" and result.lawyer_needed and not result.legal_claims


async def test_web_summary_not_used_as_law():
    assistant = AsyncMock()
    draft = answer()
    draft.legal_claims = [Claim(text="legal promise", source_ids=["web-1"])]
    result = await verify(assistant, draft, [], "facts")
    assert not result.legal_claims
    assistant.structured.assert_not_called()
