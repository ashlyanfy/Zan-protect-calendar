import io

import pytest
from pypdf import PdfReader

from app.cases import BRANCHES, Case
from app.documents import TITLES, build_draft, export


def confirmed_case():
    case = Case(branch="money")
    for key in BRANCHES["money"]:
        case.record("Ақша аударымы 300 000 теңге. Ә Ғ Қ Ң Ө Ұ Ү Һ І." if key == "story" else "Неизвестно")
    case.confirm()
    return case


@pytest.mark.parametrize("branch", list(BRANCHES))
def test_questionnaire_requires_complete_confirmation(branch):
    case = Case(branch=branch)
    with pytest.raises(ValueError):
        case.confirm()
    while case.next_field():
        assert case.question("kk")
        case.record("Неизвестно")
    assert not case.confirmed
    case.confirm()
    assert case.confirmed


@pytest.mark.parametrize("kind", list(TITLES))
@pytest.mark.parametrize("language", ["ru", "kk"])
def test_templates_preserve_confirmed_facts(kind, language):
    draft = build_draft(kind, confirmed_case(), language)
    assert "300 000" in draft.body
    assert "статья" not in draft.body.lower()
    assert draft.title


def test_unconfirmed_export_rejected():
    with pytest.raises(ValueError):
        build_draft("police", Case(branch="money"), "ru")


def test_pdf_kazakh_text_roundtrip():
    draft = build_draft("police", confirmed_case(), "kk")
    pdf = export(draft, "pdf")
    text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
    for letter in "ӘҒҚҢӨҰҮҺІ":
        assert letter in text


def test_docx_unicode_roundtrip():
    from docx import Document
    draft = build_draft("police", confirmed_case(), "kk")
    doc = Document(io.BytesIO(export(draft, "docx")))
    assert "300 000" in "\n".join(p.text for p in doc.paragraphs)
