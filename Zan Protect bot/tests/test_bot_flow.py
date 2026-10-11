import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot import Controller
from app.cases import BRANCHES, Case
from app.privacy import Session


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
    assistant = SimpleNamespace(analyze=AsyncMock())
    config = SimpleNamespace(font_path="", consultation_url="", enable_web_search=False, daily_request_limit=5,
                             max_file_bytes=1000000, max_input_chars=24000)
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


async def test_questionnaire_does_not_use_llm():
    session = Session(expires=time.time()+600, consent=True, case=Case(branch="money").model_dump())
    controller, row, _bot, assistant = setup("Сегодня утром", session)
    await controller.handle(row)
    assert session.case["facts"]["when"] == "Сегодня утром"
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
