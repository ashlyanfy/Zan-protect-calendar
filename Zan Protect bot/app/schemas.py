from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Intake(StrictModel):
    language: Literal["ru", "kk"]
    situation: Literal["check", "money", "loan", "credentials", "blocked", "dropper", "other"]
    summary: str
    indicators: list[str]
    risk_floor: Literal["unknown", "low", "medium", "high"]
    search_topic: Literal["none", "fraud_loan", "account_block", "dropper", "police_report", "phishing"]
    questions: list[str]


class DialogueTurn(StrictModel):
    action: Literal["answer", "clarify", "pause", "off_topic", "new_topic", "analyze"]
    reply: str = Field(max_length=1200)


class Source(StrictModel):
    id: str
    title: str
    url: str
    checked_on: str
    excerpt: str


class Claim(StrictModel):
    text: str
    source_ids: list[str]


class Answer(StrictModel):
    language: Literal["ru", "kk"]
    risk: Literal["unknown", "low", "medium", "high"]
    summary: str
    evidence: list[str]
    explanation: str
    immediate_actions: list[str]
    next_actions: list[str]
    questions: list[str]
    legal_claims: list[Claim]
    uncertainty: str
    lawyer_needed: bool


class AnalyzeRequest(StrictModel):
    text: str = Field(min_length=1, max_length=24000)
    mode: Literal["check", "help"] = "check"
    language: Literal["ru", "kk"] = "ru"
    web_consent: bool = False


class DocumentRequest(StrictModel):
    kind: Literal["police", "bank_dispute", "bank_loan", "regulator", "block_reason", "restructure", "evidence"]
    language: Literal["ru", "kk"] = "ru"
    facts: str = Field(min_length=1, max_length=24000)


class Draft(StrictModel):
    title: str
    body: str
    missing_fields: list[str]
    attachments: list[str]


class ExportRequest(StrictModel):
    kind: Literal["police", "bank_dispute", "bank_loan", "regulator", "block_reason", "restructure", "evidence"]
    language: Literal["ru", "kk"] = "ru"
    branch: Literal["money", "loan", "credentials", "blocked", "dropper"]
    facts: dict[str, str]
    confirmed: bool
    format: Literal["txt", "pdf", "docx"] = "pdf"
