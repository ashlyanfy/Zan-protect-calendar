"""Dialogue memory: sliding session TTL and character-budget history trimming."""
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.bot import Controller
from app.privacy import Session, trim_history


def test_trim_history_keeps_newest_within_budget():
    history = [f"сообщение {i} " + "x" * 100 for i in range(30)]
    kept = trim_history(history, 500)
    assert kept == history[-len(kept):]  # only the oldest entries are dropped
    assert 0 < len(kept) <= 5
    assert sum(len(x) + 1 for x in kept) <= 500 + len(kept[0]) + 1


def test_trim_history_never_drops_latest_entry():
    assert trim_history(["старое", "очень длинное последнее " * 50], 10) == ["очень длинное последнее " * 50]
    assert trim_history([], 100) == []


def test_trim_history_caps_item_count():
    history = ["a"] * 100
    assert len(trim_history(history, 10**6)) == 24


async def test_session_ttl_slides_on_activity():
    soon = time.time() + 120  # old fixed-TTL session about to expire mid-conversation
    session = Session(expires=soon, consent=True)
    bot_calls = []

    class FakeBot:
        async def __call__(self, method, **kwargs):
            bot_calls.append(method)
            return True

    store = SimpleNamespace(open=lambda x: x, get=AsyncMock(return_value=session), save=AsyncMock(),
                            active=AsyncMock(return_value=True), quota=AsyncMock(return_value=True))
    config = SimpleNamespace(font_path="", consultation_url="", enable_web_search=False, daily_request_limit=5,
                             max_file_bytes=1000000, max_input_chars=24000, max_audio_seconds=300,
                             session_ttl_seconds=1800)
    controller = Controller(FakeBot(), store, SimpleNamespace(), config)
    row = {"update_id": 1, "session_id": "x", "payload": {"update_id": 1, "message": {
        "message_id": 1, "date": int(time.time()), "chat": {"id": 1, "type": "private"},
        "from": {"id": 1, "is_bot": False, "first_name": "Test"}, "text": "Русский"}}}
    await controller.handle(row)
    saved = store.save.await_args.args[1]
    assert saved.expires >= time.time() + 1700  # extended to a full TTL from the last message
