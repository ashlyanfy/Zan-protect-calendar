"""End-to-end (with fakes) proof that lawyer materials reach the model as citable sources."""
from datetime import date
from types import SimpleNamespace

from app.llm import Assistant
from app.retrieval import retrieve
from app.schemas import Answer, Claim, Intake, Source


class FakeConn:
    def __init__(self, results):
        self.results = list(results)
        self.queries = []

    async def fetch(self, sql, *args):
        self.queries.append(sql)
        return self.results.pop(0)


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *exc):
        return False


async def test_retrieve_returns_lawyer_material_as_source():
    lawyer_row = {"id": "7", "title": "Памятка по мошенническим кредитам",
                  "content": "Если кредит оформлен без ведома человека, нужно сразу подать заявление в банк.",
                  "checked_on": date(2026, 11, 7)}
    conn = FakeConn([[], [], [lawyer_row]])  # scheme cards, legal sources, lawyer materials
    pool = SimpleNamespace(acquire=lambda: FakeAcquire(conn))
    cards, sources = await retrieve(pool, "мошеннический кредит банк", date(2026, 11, 7))
    assert cards == []
    assert [s.id for s in sources] == ["lawyer-7"]
    assert sources[0].title == "Памятка по мошенническим кредитам"
    assert "подать заявление в банк" in sources[0].excerpt
    assert len(conn.queries) == 3 and "lawyer_materials" in conn.queries[2]


async def test_retrieve_caps_lawyer_sources_and_keeps_legal():
    legal = [{"id": f"law-{i}", "title": f"Закон {i}", "url": "https://adilet.zan.kz/x",
              "excerpt": "Норма об ответственности.", "checked_on": date(2026, 1, 1)} for i in range(6)]
    lawyer = [{"id": str(i), "title": f"Материал {i}", "content": "Содержание материала юриста." * 3,
               "checked_on": date(2026, 11, 7)} for i in range(5)]
    conn = FakeConn([[], legal, lawyer])
    pool = SimpleNamespace(acquire=lambda: FakeAcquire(conn))
    _, sources = await retrieve(pool, "ответственность", date(2026, 11, 7))
    assert len(sources) == 6  # overall budget kept
    assert sum(s.id.startswith("lawyer-") for s in sources) == 2  # lawyer never crowds out legal sources


async def test_analyze_passes_lawyer_source_to_model_and_accepts_citation(monkeypatch):
    cfg = SimpleNamespace(openai_api_key="key", max_input_chars=24000, enable_semantic_search=False,
                          enable_web_search=False, verify_answers=False, openai_model="model",
                          reasoning_effort="low", embedding_model="e", embedding_dimensions=512)
    assistant = Assistant(cfg, None)
    lawyer_source = Source(id="lawyer-7", title="Памятка юриста", url="Внутренний материал юриста Zan Protect",
                           checked_on="2026-11-07", excerpt="Кредит, оформленный мошенниками, можно оспорить через банк и АРРФР.")

    async def fake_retrieve(pool, query, today, vector=None, model=""):
        return [], [lawyer_source]

    monkeypatch.setattr("app.llm.retrieve", fake_retrieve)
    calls = []
    intake = Intake(language="ru", situation="loan", summary="мошеннический кредит", indicators=["кредит"],
                    risk_floor="high", search_topic="none", questions=[])
    answer = Answer(language="ru", risk="high", summary="Признаки мошеннического кредита.", evidence=[],
                    explanation="", immediate_actions=[], next_actions=[], questions=[],
                    legal_claims=[Claim(text="Такой кредит можно оспорить.", source_ids=["lawyer-7"])],
                    uncertainty="", lawyer_needed=True)

    async def fake_structured(name, payload, schema, image=None):
        calls.append((name, payload))
        return intake if name == "intake" else answer

    assistant.structured = fake_structured
    result, sources = await assistant.analyze("на меня оформили кредит", "check", "ru")
    assert [s.id for s in sources] == ["lawyer-7"]
    payload = next(p for n, p in calls if n == "check")
    assert payload["sources"][0]["id"] == "lawyer-7"
    assert "можно оспорить через банк" in payload["sources"][0]["excerpt"]
    # validate_answer keeps the claim because the lawyer material is a known source
    assert result.legal_claims[0].source_ids == ["lawyer-7"]
