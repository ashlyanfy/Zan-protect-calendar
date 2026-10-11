import logging

from openai import OpenAIError

from app.schemas import Answer, Source, StrictModel

log = logging.getLogger("zan.verification")


class Review(StrictModel):
    approved: bool
    unsupported_claims: list[str]
    reason: str


def safe_fallback(language: str, situation: str = "other") -> Answer:
    kk = language == "kk"
    if situation == "blackmail":
        return Answer(language=language, risk="high",
                      summary="Сіз жариялау қаупі туралы хабарладыңыз. Алдымен қауіпсіздігіңізді қорғаңыз." if kk else
                      "Вы сообщили об угрозе публикации личных материалов. Сейчас важно защитить себя.",
                      evidence=[], explanation="", immediate_actions=[
                          "Хаттар мен аккаунт сілтемелерін сақтаңыз. Интимдік материалдарды мұнда жібермеңіз." if kk else
                          "Сохраните переписку и ссылки на аккаунты. Интимные материалы сюда не присылайте.",
                          "Жаңа жеке материалдар мен аккаунтқа кіру деректерін бермеңіз." if kk else
                          "Не передавайте новые личные материалы и данные для входа в аккаунты.",
                          "Ақша сұраса, төлем қауіптің тоқтауына кепілдік бермейді." if kk else
                          "Если требуют деньги, оплата не гарантирует прекращения угроз."],
                      next_actions=[], questions=[
                          "Сізден нақты не талап етеді және қазір физикалық қауіп бар ма?" if kk else
                          "Что именно от вас требуют и есть ли сейчас угроза физической безопасности?"],
                      legal_claims=[], uncertainty="Толық құқықтық жауапты тексеру мүмкін болмады." if kk else
                      "Подробный правовой ответ пока не удалось проверить.", lawyer_needed=False)
    return Answer(language=language, risk="unknown",
                  summary="Қорытындыны сенімді тексеру мүмкін болмады." if kk else "Не удалось надёжно проверить вывод.",
                  evidence=[], explanation="", immediate_actions=[
                      "Хаттарды сақтаңыз. Құпиясөздер мен қосымша жеке деректерді бермеңіз." if kk else
                      "Сохраните переписку. Не передавайте пароли и дополнительные личные данные."],
                  next_actions=[], questions=[], legal_claims=[],
                  uncertainty="",
                  lawyer_needed=True)


async def verify(assistant, answer: Answer, sources: list[Source], facts: str,
                 situation: str = "other") -> Answer:
    reviewed = [s for s in sources if not s.id.startswith("web-")]
    valid_ids = {s.id for s in reviewed}
    language = answer.language
    # One repair, followed by another full review. Never pass an unreviewed repair to the user.
    for attempt in range(2):
        try:
            if any(not c.source_ids or not set(c.source_ids) <= valid_ids for c in answer.legal_claims):
                review = Review(approved=False, unsupported_claims=["Invalid legal source IDs"],
                                reason="Remove unsupported law; web summaries are not verified legal sources.")
            else:
                review = await assistant.structured("verify", {
                    "answer": answer.model_dump(), "user_facts": facts,
                    "sources": [s.model_dump() for s in reviewed],
                }, Review)
            if review.approved and not review.unsupported_claims:
                return answer
            log.warning("verifier_rejected attempt=%s issues=%s", attempt + 1, len(review.unsupported_claims))
            if attempt == 0:
                answer = await assistant.structured("repair", {
                    "language": language, "situation": situation, "user_facts": facts,
                    "answer": answer.model_dump(), "review": review.model_dump(),
                    "sources": [s.model_dump() for s in reviewed],
                }, Answer)
                answer.language = language
        except (OpenAIError, ValueError, TimeoutError) as exc:
            log.warning("verifier_unavailable type=%s", type(exc).__name__)
            break
    return safe_fallback(language, situation)
