"""Generate synthetic layout fixtures only; never run on real user material."""
from pathlib import Path

from app.cases import BRANCHES, Case
from app.documents import build_draft, export


def main():
    output = Path("tmp/document-qa")
    output.mkdir(parents=True, exist_ok=True)
    for lang in ("ru", "kk"):
        case = Case(branch="money")
        answers = {"when": "11.10.2026, 10:00", "story": "Тестовый случай. После звонка перевёл 300 000 тенге." if lang == "ru" else
                   "Сынақ жағдайы. Қоңыраудан кейін 300 000 теңге аудардым. Ә Ғ Қ Ң Ө Ұ Ү Һ І.",
                   "amount": "300 000 KZT", "bank": "[Банк]", "transfer": "Подтвердил сам / Өзім растадым",
                   "access": "Доступ сохранён / Қолжетімділік бар", "evidence": "Переписка / Хаттар",
                   "contacted": "Пока не обращался / Әзірге жүгінбедім"}
        for field in BRANCHES[case.branch]:
            case.record(answers[field])
        case.confirm()
        draft = build_draft("police", case, lang)
        for fmt in ("pdf", "docx"):
            (output / f"police-{lang}.{fmt}").write_bytes(export(draft, fmt))


if __name__ == "__main__":
    main()
