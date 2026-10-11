from app.schemas import Answer, Source, StrictModel


class Review(StrictModel):
    approved: bool
    unsupported_claims: list[str]
    reason: str


def safe_fallback(language: str) -> Answer:
    kk = language == "kk"
    return Answer(language=language, risk="unknown",
                  summary="Қорытындыны сенімді тексеру мүмкін болмады." if kk else "Не удалось надёжно проверить вывод.",
                  evidence=[], explanation="", immediate_actions=[
                      "Кодтар мен құпиясөздерді бермеңіз. Банкке ресми арна арқылы хабарласыңыз." if kk else
                      "Не передавайте коды и пароли. При угрозе деньгам свяжитесь с банком через официальный канал."],
                  next_actions=[], questions=[], legal_claims=[],
                  uncertainty="Жеке жағдайды заңгермен тексеріңіз." if kk else "Проверьте индивидуальную ситуацию с юристом.",
                  lawyer_needed=True)


async def verify(assistant, answer: Answer, sources: list[Source], facts: str) -> Answer:
    reviewed = [s for s in sources if not s.id.startswith("web-")]
    # A web-search summary is not a verified legal passage.
    if any(any(x.startswith("web-") for x in claim.source_ids) for claim in answer.legal_claims):
        return safe_fallback(answer.language)
    review = await assistant.structured("verify", {
        "answer": answer.model_dump(), "user_facts": facts,
        "sources": [s.model_dump() for s in reviewed],
    }, Review)
    return answer if review.approved and not review.unsupported_claims else safe_fallback(answer.language)
