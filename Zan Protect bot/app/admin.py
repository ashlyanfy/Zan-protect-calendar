"""Lawyer admin panel inside the Telegram bot, gated by ADMIN_IDS from config."""
import asyncio
import io
import logging
import time

from aiogram.types import BufferedInputFile, KeyboardButton, Message, ReplyKeyboardMarkup

from app.files import extract
from app.knowledge import index_knowledge
from app.llm import prompt

log = logging.getLogger("zan.admin")

PROMPTS = {
    "system": "базовые правила, стиль и границы (общая часть всех ответов)",
    "dialogue": "ведение диалога и анкеты",
    "intake": "первичный разбор обращения",
    "check": "режим «Проверь» — оценка риска",
    "help": "режим «Уже случилось» — план действий",
    "document": "черновики заявлений и обращений",
    "verify": "проверка ответа перед отправкой",
    "repair": "исправление отклонённого ответа",
}
SECTIONS = {"Промпты", "Стиль общения", "Материалы", "Контакт юриста", "Статус"}
MAX_PROMPT = 24000
MAX_STYLE = 4000
MAX_CONTACT = 1000
MIN_MATERIAL = 60
STATE_TTL = 1800


def keyboard(rows):
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=x) for x in row] for row in rows], resize_keyboard=True)


ADMIN_MENU = keyboard([["Промпты", "Стиль общения"], ["Материалы", "Контакт юриста"], ["Статус", "Выход"]])
PROMPT_MENU = keyboard([["system", "dialogue", "intake"], ["check", "help", "document"], ["verify", "repair"], ["Назад", "Выход"]])
BACK_MENU = keyboard([["Назад", "Выход"]])

WELCOME = (
    "Режим администратора Zan Protect.\n\n"
    "Промпты — инструкции, по которым отвечает ИИ. Можно переписать любую часть.\n"
    "Стиль общения — ваши указания, как ИИ должен разговаривать с людьми.\n"
    "Материалы — загрузите документы (PDF, DOCX, TXT), и ИИ будет опираться на них в ответах.\n"
    "Контакт юриста — что бот отвечает на кнопку «Юрист / Заңгер».\n\n"
    "Все изменения действуют сразу, без перезапуска. «Выход» возвращает в обычный режим."
)


class AdminPanel:
    def __init__(self, bot, pool, store, assistant, cfg, user_menu):
        self.bot, self.pool, self.store, self.assistant, self.cfg = bot, pool, store, assistant, cfg
        self.user_menu = user_menu
        self.admins = cfg.admin_id_set()
        self.states: dict[int, dict] = {}
        self._tasks: set[asyncio.Task] = set()

    def claims(self, user_id: int, text: str) -> bool:
        """Decide synchronously whether this update belongs to the admin flow."""
        if user_id not in self.admins:
            return False
        if text.strip() == "/admin":
            return True
        entry = self.states.get(user_id)
        return bool(entry and entry["expires"] > time.time())

    def spawn(self, message: Message):
        task = asyncio.create_task(self.handle(message))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def set_state(self, user_id: int, state: str):
        self.states[user_id] = {"state": state, "expires": time.time() + STATE_TTL}

    async def audit(self, kind: str, item_id: str, action: str, actor: str):
        await self.pool.execute("INSERT INTO editorial_audit(kind,item_id,action,actor) VALUES($1,$2,$3,$4)",
                                kind, item_id, action, actor)

    async def handle(self, message: Message):
        try:
            await self.dispatch(message)
        except Exception as exc:  # noqa: BLE001 -- keep the poll loop alive; admin is trusted staff
            log.warning("admin_failed type=%s", type(exc).__name__)
            try:
                await message.answer(f"Не получилось выполнить действие ({type(exc).__name__}). Попробуйте ещё раз.",
                                     reply_markup=ADMIN_MENU, parse_mode=None)
            except Exception:  # noqa: BLE001
                pass

    async def dispatch(self, message: Message):
        user_id = message.from_user.id
        actor = str(user_id)
        text = (message.text or message.caption or "").strip()
        entry = self.states.get(user_id)
        state = entry["state"] if entry and entry["expires"] > time.time() else ""

        async def send(body: str, markup=None, filename: str | None = None):
            if filename and len(body) > 3000:
                await message.answer_document(BufferedInputFile(body.encode("utf-8"), filename=filename))
                body = "Текст выше отправлен файлом."
            chunks = [body[i:i + 3500] for i in range(0, len(body), 3500)] or [body]
            for index, chunk in enumerate(chunks):
                await message.answer(chunk, reply_markup=markup if index == len(chunks) - 1 else None,
                                     parse_mode=None, disable_web_page_preview=True)

        if text == "Выход":
            self.states.pop(user_id, None)
            await send("Режим администратора закрыт. Бот снова работает как для обычного пользователя.", self.user_menu)
            return
        if text in {"/admin", "Назад"}:
            self.set_state(user_id, "menu")
            await send(WELCOME, ADMIN_MENU)
            return
        if text in SECTIONS:
            await self.open_section(text, user_id, send)
            return
        if state == "prompts" and text in PROMPTS:
            self.set_state(user_id, f"prompt:{text}")
            current = await self.store.get_setting(f"prompt:{text}")
            origin = "ИЗМЕНЁН юристом" if current else "стандартный (из файла)"
            await send(f"Промпт «{text}» — {PROMPTS[text]}.\nТекущий вариант: {origin}.", None)
            await send(current or prompt(text), None, filename=f"{text}.txt")
            await send("Пришлите новый текст сообщением или файлом .txt — он заменит этот промпт сразу.\n"
                       "/default — вернуть стандартный вариант.", BACK_MENU)
            return
        if state.startswith("prompt:"):
            await self.edit_prompt(state.split(":", 1)[1], message, text, actor, send)
            return
        if state == "style":
            await self.edit_setting("style_guide", text, MAX_STYLE, actor, send,
                                    "Стиль сохранён. ИИ будет учитывать его в каждом ответе.",
                                    "Указания стиля удалены, действует стандартный стиль.")
            return
        if state == "contact":
            await self.edit_setting("consultation_contact", text, MAX_CONTACT, actor, send,
                                    "Контакт сохранён. Кнопка «Юрист / Заңгер» теперь отвечает этим текстом.",
                                    "Контакт удалён. Будет использоваться значение из настроек сервера, если задано.")
            return
        if state == "materials":
            await self.handle_material(message, text, actor, send)
            return
        self.set_state(user_id, "menu")
        await send(WELCOME, ADMIN_MENU)

    async def open_section(self, section: str, user_id: int, send):
        if section == "Промпты":
            self.set_state(user_id, "prompts")
            lines = [f"{name} — {hint}" for name, hint in PROMPTS.items()]
            overridden = [r["key"].removeprefix("prompt:") for r in
                          await self.pool.fetch("SELECT key FROM bot_settings WHERE key LIKE 'prompt:%'")]
            note = ("Изменены юристом: " + ", ".join(sorted(overridden))) if overridden else "Все промпты стандартные."
            await send("Выберите промпт кнопкой:\n\n" + "\n".join(lines) + "\n\n" + note, PROMPT_MENU)
        elif section == "Стиль общения":
            self.set_state(user_id, "style")
            current = await self.store.get_setting("style_guide")
            await send("Стиль общения — ваши указания, как ИИ разговаривает: тон, обращение, примеры формулировок.\n"
                       f"Сейчас: {current or 'не задан, действует стандартный стиль.'}\n\n"
                       "Пришлите указания одним сообщением (до 4000 знаков). /default — убрать.", BACK_MENU)
        elif section == "Контакт юриста":
            self.set_state(user_id, "contact")
            current = await self.store.get_setting("consultation_contact") or self.cfg.consultation_url
            await send("Это ответ бота на кнопку «Юрист / Заңгер».\n"
                       f"Сейчас: {current or 'не настроен.'}\n\n"
                       "Пришлите новый текст: ссылку, телефон или описание, как записаться. /default — убрать.", BACK_MENU)
        elif section == "Материалы":
            self.set_state(user_id, "materials")
            await send("Материалы юриста — база знаний ИИ. Он находит подходящий материал и ссылается на него в ответах.\n\n" +
                       await self.materials_list() +
                       "\n\nПришлите документ (PDF, DOCX, TXT) — подпись к файлу станет названием.\n"
                       "Или пришлите текст: первая строка — название, дальше — содержание.\n"
                       "/show N — показать материал N. /del N — удалить материал N.", BACK_MENU)
        else:
            await self.status(send)

    async def status(self, send):
        overrides = [r["key"] for r in await self.pool.fetch("SELECT key FROM bot_settings ORDER BY key")]
        prompts = [k.removeprefix("prompt:") for k in overrides if k.startswith("prompt:")]
        materials = await self.pool.fetchval("SELECT count(*) FROM lawyer_materials WHERE active")
        contact = "style_guide" in overrides, "consultation_contact" in overrides
        await send("Состояние:\n"
                   f"• Промпты, изменённые юристом: {', '.join(prompts) if prompts else 'нет'}\n"
                   f"• Стиль общения: {'задан' if contact[0] else 'стандартный'}\n"
                   f"• Контакт юриста: {'задан в боте' if contact[1] else ('из настроек сервера' if self.cfg.consultation_url else 'не задан')}\n"
                   f"• Материалов в базе знаний: {materials}", ADMIN_MENU)

    async def materials_list(self) -> str:
        rows = await self.pool.fetch(
            "SELECT id,title,length(content) AS size,created_at::date AS day FROM lawyer_materials WHERE active ORDER BY id")
        if not rows:
            return "Материалов пока нет."
        return "\n".join(f"{r['id']}. {r['title']} — {r['size']} зн., добавлен {r['day']}" for r in rows)

    async def download(self, document) -> bytes:
        if document.file_size is None or document.file_size > self.cfg.max_file_bytes:
            raise ValueError("File size limit")
        output = io.BytesIO()
        await self.bot.download(document.file_id, destination=output, timeout=60)
        return output.getvalue()

    async def edit_prompt(self, name: str, message: Message, text: str, actor: str, send):
        if text == "/default":
            await self.store.set_setting(f"prompt:{name}", "", actor)
            await self.audit("prompt", name, "reset_default", actor)
            await send(f"Промпт «{name}» возвращён к стандартному варианту.", PROMPT_MENU)
            return
        if message.document:
            raw = await self.download(message.document)
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                await send("Файл должен быть обычным текстом в кодировке UTF-8 (.txt).", BACK_MENU)
                return
        text = text.strip()
        if not text:
            await send("Пришлите текст промпта сообщением или файлом .txt, либо /default.", BACK_MENU)
            return
        if len(text) > MAX_PROMPT:
            await send(f"Слишком длинно: {len(text)} знаков при лимите {MAX_PROMPT}.", BACK_MENU)
            return
        await self.store.set_setting(f"prompt:{name}", text, actor)
        await self.audit("prompt", name, "override", actor)
        await send(f"Промпт «{name}» сохранён ({len(text)} знаков). Изменение уже действует.", PROMPT_MENU)

    async def edit_setting(self, key: str, text: str, limit: int, actor: str, send, saved: str, cleared: str):
        if text == "/default":
            await self.store.set_setting(key, "", actor)
            await self.audit("setting", key, "reset_default", actor)
            await send(cleared, ADMIN_MENU)
            return
        if not text:
            await send("Пришлите текст одним сообщением, либо /default.", BACK_MENU)
            return
        if len(text) > limit:
            await send(f"Слишком длинно: {len(text)} знаков при лимите {limit}.", BACK_MENU)
            return
        await self.store.set_setting(key, text, actor)
        await self.audit("setting", key, "update", actor)
        await send(saved, ADMIN_MENU)

    async def handle_material(self, message: Message, text: str, actor: str, send):
        if text.startswith("/del"):
            item = text.removeprefix("/del").strip()
            if not item.isdigit():
                await send("Укажите номер: /del 3", BACK_MENU)
                return
            deleted = await self.pool.fetchval("DELETE FROM lawyer_materials WHERE id=$1 RETURNING id", int(item))
            if deleted is None:
                await send(f"Материала {item} нет.", BACK_MENU)
                return
            await self.pool.execute("DELETE FROM knowledge_embeddings WHERE kind='lawyer' AND item_id=$1", item)
            await self.audit("lawyer", item, "delete", actor)
            await send(f"Материал {item} удалён.\n\n" + await self.materials_list(), BACK_MENU)
            return
        if text.startswith("/show"):
            item = text.removeprefix("/show").strip()
            row = await self.pool.fetchrow("SELECT title,content FROM lawyer_materials WHERE id=$1 AND active",
                                           int(item)) if item.isdigit() else None
            if not row:
                await send("Укажите номер существующего материала: /show 3", BACK_MENU)
                return
            await send(row["title"] + "\n\n" + row["content"], BACK_MENU, filename=f"material-{item}.txt")
            return
        title, content = "", ""
        if message.document:
            raw = await self.download(message.document)
            name = message.document.file_name or "document.txt"
            extracted = await extract(name, raw)
            content = extracted["text"].strip()
            if not content:
                await send("Из файла не удалось извлечь текст. Пришлите PDF, DOCX или TXT с текстом,"
                           " либо отправьте содержание сообщением.", BACK_MENU)
                return
            title = text.splitlines()[0].strip() if text else name
        elif text:
            lines = text.splitlines()
            title, content = lines[0].strip(), "\n".join(lines[1:]).strip() or text
        if not content:
            await send("Пришлите документ (PDF, DOCX, TXT) или текст: первая строка — название.", BACK_MENU)
            return
        if len(content) < MIN_MATERIAL:
            await send(f"Материал слишком короткий ({len(content)} знаков). Нужен содержательный текст от {MIN_MATERIAL} знаков.",
                       BACK_MENU)
            return
        title = " ".join(title.split())[:150] or "Материал юриста"
        item = await self.pool.fetchval(
            "INSERT INTO lawyer_materials(title,content,uploaded_by) VALUES($1,$2,$3) RETURNING id",
            title, content[:MAX_PROMPT], actor)
        await self.audit("lawyer", str(item), "upload", actor)
        self.schedule_index()
        await send(f"Материал {item} «{title}» добавлен ({len(content)} знаков). ИИ уже может на него опираться.\n\n" +
                   await self.materials_list(), BACK_MENU)

    def schedule_index(self):
        if not (self.cfg.enable_semantic_search and self.cfg.openai_api_key):
            return
        task = asyncio.create_task(self._index())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _index(self):
        try:
            await index_knowledge(self.pool, self.assistant.client, self.cfg)
        except Exception as exc:  # noqa: BLE001 -- semantic index is best effort; lexical search still works
            log.warning("admin_index_failed type=%s", type(exc).__name__)
