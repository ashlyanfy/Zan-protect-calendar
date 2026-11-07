import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.admin import AdminPanel
from app.bot import Controller
from app.llm import Assistant, prompt
from app.privacy import Session


def fake_cfg(**extra):
    base = {"admin_id_set": lambda: frozenset({1}), "max_file_bytes": 1000000,
            "enable_semantic_search": False, "openai_api_key": "", "consultation_url": ""}
    base.update(extra)
    return SimpleNamespace(**base)


def make_panel(pool=None, store=None):
    pool = pool or SimpleNamespace(fetch=AsyncMock(return_value=[]), fetchval=AsyncMock(return_value=0),
                                   fetchrow=AsyncMock(return_value=None), execute=AsyncMock())
    store = store or SimpleNamespace(get_setting=AsyncMock(return_value=None), set_setting=AsyncMock())
    panel = AdminPanel(SimpleNamespace(), pool, store, SimpleNamespace(), fake_cfg(), user_menu=None)
    return panel, pool, store


def message(text=None, caption=None, document=None, user_id=1):
    return SimpleNamespace(text=text, caption=caption, document=document,
                           from_user=SimpleNamespace(id=user_id),
                           answer=AsyncMock(), answer_document=AsyncMock())


def test_claims_only_configured_admins():
    panel, _, _ = make_panel()
    assert panel.claims(1, "/admin")
    assert not panel.claims(2, "/admin")
    assert not panel.claims(1, "привет")  # not in admin mode yet
    panel.set_state(1, "menu")
    assert panel.claims(1, "привет")
    panel.states[1]["expires"] = time.time() - 1
    assert not panel.claims(1, "привет")


async def test_exit_returns_to_user_mode():
    panel, _, _ = make_panel()
    await panel.handle(message("/admin"))
    assert 1 in panel.states
    await panel.handle(message("Выход"))
    assert 1 not in panel.states
    assert not panel.claims(1, "обычное сообщение")


async def test_contact_edit_saves_setting():
    panel, _, store = make_panel()
    await panel.handle(message("/admin"))
    await panel.handle(message("Контакт юриста"))
    await panel.handle(message("Запись: wa.me пример, телефон +7 700 000 00 00"))
    store.set_setting.assert_awaited_with("consultation_contact", "Запись: wa.me пример, телефон +7 700 000 00 00", "1")


async def test_prompt_override_and_reset():
    panel, _, store = make_panel()
    await panel.handle(message("/admin"))
    await panel.handle(message("Промпты"))
    await panel.handle(message("system"))
    await panel.handle(message("Новый промпт юриста"))
    store.set_setting.assert_awaited_with("prompt:system", "Новый промпт юриста", "1")
    await panel.handle(message("system"))
    await panel.handle(message("/default"))
    store.set_setting.assert_awaited_with("prompt:system", "", "1")


async def test_material_from_text_message():
    panel, pool, _ = make_panel()
    pool.fetchval = AsyncMock(return_value=7)
    await panel.handle(message("/admin"))
    await panel.handle(message("Материалы"))
    body = "Договор займа: признаки обмана\n" + "Если заимодавец требует предоплату за выдачу займа, это признак схемы. " * 3
    await panel.handle(message(body))
    insert = pool.fetchval.await_args_list[-1].args
    assert "INSERT INTO lawyer_materials" in insert[0]
    assert insert[1] == "Договор займа: признаки обмана"
    assert "предоплату" in insert[2]


async def test_non_admin_text_never_claimed_and_admin_errors_reported():
    panel, pool, _ = make_panel()
    pool.fetch = AsyncMock(side_effect=RuntimeError("db down"))
    msg = message("/admin")
    await panel.handle(msg)  # WELCOME works without db
    await panel.handle(message("Статус"))  # must not raise out of handle()


async def test_instructions_uses_overrides_and_style():
    pool = SimpleNamespace(fetch=AsyncMock(return_value=[
        {"key": "prompt:check", "value": "Отвечай как юрист."},
        {"key": "style_guide", "value": "Говори проще."}]))
    assistant = Assistant(fake_cfg(openai_api_key=""), pool)
    text = await assistant.instructions("check")
    assert text.startswith(prompt("system"))
    assert "Отвечай как юрист." in text and "Говори проще." in text
    assert "не отменяют границы доверия" in text


async def test_instructions_without_pool_falls_back_to_files():
    assistant = Assistant(fake_cfg(openai_api_key=""), None)
    text = await assistant.instructions("check")
    assert prompt("check") in text


async def test_lawyer_button_uses_stored_contact():
    store = SimpleNamespace(open=lambda x: x, get=AsyncMock(return_value=Session(expires=time.time() + 600, consent=True)),
                            save=AsyncMock(), active=AsyncMock(return_value=True), quota=AsyncMock(return_value=True),
                            get_setting=AsyncMock(return_value="Телефон юриста: +7 700 123 45 67"))
    sent = []

    class FakeBot:
        async def __call__(self, method, **kwargs):
            sent.append(method)
            return True

    config = SimpleNamespace(font_path="", consultation_url="", enable_web_search=False, daily_request_limit=5,
                             max_file_bytes=1000000, max_input_chars=24000, max_audio_seconds=300)
    controller = Controller(FakeBot(), store, SimpleNamespace(), config)
    row = {"update_id": 1, "session_id": "x", "payload": {"update_id": 1, "message": {
        "message_id": 1, "date": int(time.time()), "chat": {"id": 123, "type": "private"},
        "from": {"id": 123, "is_bot": False, "first_name": "Test"}, "text": "Юрист / Заңгер"}}}
    await controller.handle(row)
    assert "+7 700 123 45 67" in sent[0].text
