"""Welcome notice stays short without AI mentions; the first message is answered, not ignored."""
import re
import time
from unittest.mock import AsyncMock

from app.bot import NOTICE
from app.privacy import Session
from app.schemas import DialogueTurn
from tests.test_bot_flow import setup


def test_notice_is_short_and_does_not_mention_ai():
    assert len(NOTICE) < 1600
    assert re.search(r"\bИИ\b", NOTICE) is None  # «ИИН» остаётся, упоминаний ИИ нет
    assert "ЖИ" not in NOTICE
    assert "Согласен / Келісемін" in NOTICE and "/delete" in NOTICE


async def test_message_before_consent_is_kept_not_dropped():
    session = Session(expires=time.time() + 600)
    controller, row, bot, assistant = setup("Меня задоксили и угрожают публикацией, что делать?", session)
    await controller.handle(row)
    assistant.dialogue.assert_not_called()  # consent first: nothing goes to the model yet
    assert session.pending.startswith("Меня задоксили")
    assert bot.sent  # notice shown


async def test_consent_answers_the_saved_message_immediately():
    session = Session(expires=time.time() + 600, pending="Меня задоксили и угрожают публикацией, что делать?")
    controller, row, bot, assistant = setup("Согласен / Келісемін", session)
    assistant.dialogue = AsyncMock(return_value=DialogueTurn(action="clarify", reply="Уточните, кто угрожает."))
    await controller.handle(row)
    assert "задоксили" in assistant.dialogue.await_args.args[0]
    assert session.pending == ""
    assert any("Уточните" in m.text for m in bot.sent)


async def test_consent_without_pending_keeps_mode_prompt():
    session = Session(expires=time.time() + 600)
    controller, row, bot, assistant = setup("Согласен / Келісемін", session)
    await controller.handle(row)
    assistant.dialogue.assert_not_called()
    assert "Выберите режим" in bot.sent[0].text
