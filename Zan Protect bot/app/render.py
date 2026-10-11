from app.schemas import Answer, Source


def render(answer: Answer, sources: list[Source]) -> str:
    kk = answer.language == "kk"
    risks = ({"high": "Жоғары", "medium": "Орташа", "low": "Төмен", "unknown": "Дерек жеткіліксіз"}
             if kk else {"high": "Высокий", "medium": "Средний", "low": "Низкий", "unknown": "Недостаточно данных"})
    blocks = [("Тәуекел: " if kk else "Риск: ") + risks[answer.risk], answer.summary, answer.explanation]
    for title, rows in [("Белгілер" if kk else "Признаки", answer.evidence),
                        ("Қазір" if kk else "Сейчас", answer.immediate_actions),
                        ("Келесі қадамдар" if kk else "Далее", answer.next_actions),
                        ("Нақтылау" if kk else "Уточните", answer.questions)]:
        if rows:
            blocks.append(title + "\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(rows, 1)))
    used = set()
    for claim in answer.legal_claims:
        blocks.append(claim.text + " [" + ", ".join(claim.source_ids) + "]")
        used.update(claim.source_ids)
    for source in sources:
        if source.id in used:
            blocks.append(f"[{source.id}] {source.title}\n{source.url}\n" +
                          ("Тексерілген: " if kk else "Проверено: ") + source.checked_on)
    if answer.uncertainty:
        blocks.append(answer.uncertainty)
    if answer.lawyer_needed:
        blocks.append("Заңгердің жеке кеңесі қажет." if kk else "Нужна индивидуальная консультация юриста.")
    blocks.append("Ақпараттық көмек. Нәтижеге кепілдік берілмейді." if kk else
                  "Информационная помощь. Результат обращения не гарантирован.")
    return "\n\n".join(block for block in blocks if block.strip())
