import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot import Controller
from app.cases import BRANCHES, Case
from app.privacy import Session
from app.schemas import Answer, DialogueTurn


class FakeBot:
    def __init__(self):
        self.sent = []

    async def __call__(self, method, **kwargs):
        self.sent.append(method)
        return True


def setup(text, session):
    bot = FakeBot()
    store = SimpleNamespace(open=lambda x: x, get=AsyncMock(return_value=session),
                            save=AsyncMock(), active=AsyncMock(return_value=True), quota=AsyncMock(return_value=True))
    assistant = SimpleNamespace(analyze=AsyncMock(), dialogue=AsyncMock(
        return_value=DialogueTurn(action="answer", reply="")), transcribe=AsyncMock())
    config = SimpleNamespace(font_path="", consultation_url="", enable_web_search=False, daily_request_limit=5,
                             max_file_bytes=1000000, max_input_chars=24000, max_audio_seconds=300)
    row = {"update_id": 1, "session_id": "x", "payload": {"update_id": 1, "message": {
        "message_id": 1, "date": int(time.time()), "chat": {"id": 123, "type": "private"},
        "from": {"id": 123, "is_bot": False, "first_name": "Test"}, "text": text}}}
    return Controller(bot, store, assistant, config), row, bot, assistant


async def test_no_consent_no_llm():
    controller, row, bot, assistant = setup("check this", Session(expires=time.time()+600))
    await controller.handle(row)
    assistant.analyze.assert_not_called()
    assert bot.sent


async def test_help_immediate_actions_before_llm():
    controller, row, bot, assistant = setup("/help_mode", Session(expires=time.time()+600, consent=True))
    await controller.handle(row)
    assert "банк" in bot.sent[0].text
    assistant.analyze.assert_not_called()


async def test_questionnaire_checks_intent_before_recording():
    session = Session(expires=time.time()+600, consent=True, case=Case(branch="money").model_dump())
    controller, row, _bot, assistant = setup("Сегодня утром", session)
    await controller.handle(row)
    assert session.case["facts"]["when"] == "Сегодня утром"
    assistant.dialogue.assert_awaited_once()
    assistant.analyze.assert_not_called()


async def test_confirmed_pdf_delivery():
    case = Case(branch="money")
    for _ in BRANCHES["money"]:
        case.record("Неизвестно")
    case.confirm()
    controller, row, bot, assistant = setup("/document police pdf", Session(
        expires=time.time()+600, consent=True, case=case.model_dump()))
    await controller.handle(row)
    assert bot.sent[0].document.data.startswith(b"%PDF")
    assistant.analyze.assert_not_called()


async def test_cancelled_job_sends_no_result():
    controller, row, bot, _ = setup("/help", Session(expires=time.time()+600, consent=True))
    controller.store.active.return_value = False
    import asyncio
    with pytest.raises(asyncio.CancelledError):
        await controller.handle(row)
    assert not bot.sent


def answer():
    return Answer(language="ru", risk="high", summary="Разберём угрозу публикации.", evidence=[],
                  explanation="", immediate_actions=[], next_actions=[], questions=[], legal_claims=[],
                  uncertainty="", lawyer_needed=False)


async def test_threat_interrupts_bank_questionnaire():
    case = Case(branch="blocked", facts={"when": "Сегодня", "bank": "Банк"})
    session = Session(expires=time.time()+600, consent=True, case=case.model_dump(), history=["старый банк"])
    controller, row, bot, assistant = setup("Помоги, мне угрожают слить нюдсы", session)
    assistant.dialogue.return_value = DialogueTurn(action="new_topic", reply="")
    assistant.analyze.return_value = (answer(), [])
    await controller.handle(row)
    assert "notice" not in session.case["facts"]
    assert session.case_paused
    analyzed = assistant.analyze.call_args.args[0]
    assert "нюдсы" in analyzed and "старый банк" not in analyzed
    assert not any("Откуда поступили" in x.text for x in bot.sent)


@pytest.mark.parametrize("action,text", [("pause", "Хватит вопросов"), ("off_topic", "Какая погода?"),
                                         ("clarify", "Чел")])
async def test_nonanswers_never_fill_case(action, text):
    session = Session(expires=time.time()+600, consent=True, case=Case(branch="money").model_dump())
    controller, row, bot, assistant = setup(text, session)
    assistant.dialogue.return_value = DialogueTurn(action=action, reply="Уточните, какая помощь нужна.")
    await controller.handle(row)
    assert session.case["facts"] == {}
    assert session.case_paused == (action != "clarify")
    assistant.analyze.assert_not_called()
    assert len(bot.sent) == 1


async def test_analysis_failure_keeps_questionnaire_paused():
    session = Session(expires=time.time()+600, consent=True, case=Case(branch="blocked").model_dump())
    controller, row, _, assistant = setup("Мне угрожают", session)
    assistant.dialogue.return_value = DialogueTurn(action="new_topic", reply="")
    assistant.analyze.side_effect = RuntimeError("provider unavailable")
    with pytest.raises(RuntimeError):
        await controller.handle(row)
    assert session.case_paused
    controller.store.save.assert_awaited()


async def test_resume_requires_explicit_command():
    session = Session(expires=time.time()+600, consent=True, case_paused=True,
                      case=Case(branch="blocked").model_dump())
    controller, row, _, assistant = setup("/resume", session)
    await controller.handle(row)
    assert not session.case_paused
    assistant.dialogue.assert_not_called()


def voice_row(row, duration=12):
    row["payload"]["message"].pop("text")
    row["payload"]["message"]["voice"] = {
        "file_id": "test-voice", "file_unique_id": "test", "duration": duration, "file_size": 100,
        "mime_type": "audio/ogg"}


async def test_audio_requires_separate_consent_before_download():
    controller, row, bot, assistant = setup("", Session(expires=time.time()+600, consent=True))
    voice_row(row)
    bot.download = AsyncMock()
    await controller.handle(row)
    bot.download.assert_not_called()
    assistant.transcribe.assert_not_called()
    assert "внешнему ИИ" in bot.sent[0].text


async def test_voice_transcript_uses_dialogue_routing():
    session = Session(expires=time.time()+600, consent=True, audio_consent=True,
                      case=Case(branch="blocked").model_dump())
    controller, row, bot, assistant = setup("", session)
    voice_row(row)

    async def download(file_id, destination, **kwargs):
        destination.write(b"fake-audio")

    bot.download = download
    assistant.transcribe.return_value = "Мне угрожают публикацией фото"
    assistant.dialogue.return_value = DialogueTurn(action="new_topic", reply="")
    assistant.analyze.return_value = (answer(), [])
    await controller.handle(row)
    assistant.transcribe.assert_awaited_once_with("voice.ogg", b"fake-audio")
    assert "публикацией" in assistant.dialogue.call_args.args[0]
    assert session.case["facts"] == {} and session.case_paused


async def test_long_voice_rejected_before_download():
    controller, row, bot, assistant = setup("", Session(expires=time.time()+600, consent=True, audio_consent=True))
    voice_row(row, 301)
    bot.download = AsyncMock()
    await controller.handle(row)
    bot.download.assert_not_called()
    assistant.transcribe.assert_not_called()
