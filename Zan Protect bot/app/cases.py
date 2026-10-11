"""Deterministic questionnaires. User confirms every collected fact before export."""
from pydantic import BaseModel, Field, field_validator

QUESTIONS = {
    "when": ("Когда это произошло? Укажите дату и примерное время либо «не знаю».", "Бұл қашан болды? Күні мен шамамен уақытын жазыңыз немесе «білмеймін» деңіз."),
    "story": ("Кратко опишите события: что предложили и что вы сделали. Без паролей и кодов.", "Оқиғаны қысқаша сипаттаңыз: не ұсынды және не істедіңіз? Құпиясөздер мен кодтарсыз."),
    "amount": ("Какая сумма и валюта? Если неизвестно — «не знаю».", "Сомасы мен валютасы қандай? Белгісіз болса — «білмеймін»."),
    "bank": ("Как называется банк или организация? Не указывайте номер карты.", "Банк не ұйым қалай аталады? Карта нөмірін жазбаңыз."),
    "transfer": ("Вы сами подтвердили перевод или заметили неизвестную операцию?", "Аударымды өзіңіз растадыңыз ба, әлде белгісіз операцияны байқадыңыз ба?"),
    "access": ("Сохраняется ли доступ к аккаунту и продолжаются ли списания?", "Аккаунтқа кіре аласыз ба? Ақша алу жалғасып жатыр ма?"),
    "notice": ("Что написано в уведомлении о блокировке или кредите? Уберите личные данные.", "Бұғаттау не несие туралы хабарламада не жазылған? Жеке деректерді алып тастаңыз."),
    "origin": ("Откуда поступили деньги и чем это можно подтвердить?", "Ақша қайдан түсті және оны немен растай аласыз?"),
    "participation": ("Что уже передали или сделали по предложению «работодателя»?", "«Жұмыс берушінің» ұсынысы бойынша не бердіңіз не істедіңіз?"),
    "evidence": ("Какие доказательства у вас есть: переписка, выписка, договор? Не придумывайте отсутствующие.", "Қандай дәлелдер бар: хаттар, үзінді көшірме, шарт? Жоқ құжаттарды қоспаңыз."),
    "contacted": ("Куда уже обращались и какой ответ получили? Если ещё никуда — так и напишите.", "Қайда жүгіндіңіз және қандай жауап алдыңыз? Ешқайда жүгінбесеңіз, солай жазыңыз."),
}
BRANCHES = {
    "money": ["when", "story", "amount", "bank", "transfer", "access", "evidence", "contacted"],
    "loan": ["when", "story", "amount", "bank", "notice", "evidence", "contacted"],
    "credentials": ["when", "story", "bank", "access", "evidence", "contacted"],
    "blocked": ["when", "bank", "notice", "origin", "amount", "evidence", "contacted"],
    "dropper": ["when", "story", "participation", "bank", "amount", "evidence", "contacted"],
}
LABELS = {
    "when": ("Дата и время", "Күні мен уақыты"), "story": ("Обстоятельства", "Мән-жайлар"),
    "amount": ("Сумма", "Сомасы"), "bank": ("Организация", "Ұйым"),
    "transfer": ("Подтверждение операции", "Операцияны растау"), "access": ("Доступ и списания", "Кіру және ақша алу"),
    "notice": ("Уведомление", "Хабарлама"), "origin": ("Происхождение средств", "Ақшаның шығу тегі"),
    "participation": ("Совершённые действия", "Жасалған әрекеттер"),
    "evidence": ("Имеющиеся доказательства", "Қолда бар дәлелдер"), "contacted": ("Предыдущие обращения", "Бұрынғы өтініштер"),
}


class Case(BaseModel):
    branch: str = ""
    facts: dict[str, str] = Field(default_factory=dict)
    confirmed: bool = False

    @field_validator("facts")
    @classmethod
    def valid_facts(cls, facts):
        if any(key not in LABELS or not value.strip() or len(value) > 3000 for key, value in facts.items()):
            raise ValueError("Invalid fact field or length")
        return facts

    def next_field(self) -> str | None:
        return next((key for key in BRANCHES.get(self.branch, []) if key not in self.facts), None)

    def question(self, language: str) -> str | None:
        key = self.next_field()
        return QUESTIONS[key][language == "kk"] if key else None

    def record(self, text: str):
        key = self.next_field()
        if not key or not text.strip() or len(text) > 3000:
            raise ValueError("Invalid questionnaire answer")
        self.facts[key] = text.strip()
        self.confirmed = False

    def summary(self, language: str) -> str:
        return "\n".join(f"{LABELS[k][language == 'kk']}: {v}" for k, v in self.facts.items() if k in LABELS)

    def confirm(self):
        if self.branch not in BRANCHES or self.next_field():
            raise ValueError("Questionnaire incomplete")
        self.confirmed = True
