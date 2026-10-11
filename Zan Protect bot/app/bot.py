"""Encrypted PostgreSQL sessions and durable bounded Telegram processing."""
import asyncio
import hashlib
import io
import logging
import signal
import time

import asyncpg
from aiogram import Bot
from aiogram.types import BufferedInputFile, KeyboardButton, Message, ReplyKeyboardMarkup, Update

from app.audio import audio_attachment
from app.cases import Case
from app.config import settings
from app.documents import TITLES, build_draft, export
from app.files import extract
from app.llm import Assistant
from app.privacy import redact, session_key
from app.render import render
from app.storage import PrivateStore
from scripts.migrate import migrate_database

log = logging.getLogger("zan.runtime")
BRANCH_BUTTONS = {"Деньги ушли / Ақша кетті": "money", "Чужой кредит / Бөтен несие": "loan",
                  "Передал доступ / Қолжетімділік бердім": "credentials",
                  "Счёт заблокирован / Шот бұғатталды": "blocked", "Работа с картой / Картамен жұмыс": "dropper"}


def keyboard(rows):
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=x) for x in row] for row in rows], resize_keyboard=True)


MENU = keyboard([["Проверь / Тексер", "Уже случилось / Болып қойды"], ["Русский", "Қазақша"],
                 ["Согласен / Келісемін", "Юрист / Заңгер"]])
HELP_MENU = keyboard([[x] for x in BRANCH_BUTTONS])
AUDIO_CONSENT = "Разрешить аудио / Аудиоға келісемін"
NOTICE = (
    "Zan Protect — помощь по мошенничеству в Казахстане. Текст и изображения обрабатываются внешним ИИ. "
    "Для расшифровки аудио отдельно запрашивается согласие на отправку записи внешнему ИИ. "
    "Не отправляйте пароли, коды, ИИН и номера карт. Скройте личные данные на изображениях. "
    "Зашифрованная сессия хранится до 30 минут; /delete отменяет обработку и удаляет активные данные. "
    "Это не удаляет историю Telegram, данные провайдера и ранее созданные резервные копии. "
    "Для обработки нажмите «Согласен / Келісемін».\n\n"
    "Қазақстандағы алаяқтық бойынша көмек. Мәтін мен суреттер сыртқы ЖИ сервисіне жіберіледі. "
    "Аудионы сыртқы ЖИ арқылы мәтінге айналдыруға бөлек келісім сұралады. "
    "Құпиясөз, код, ЖСН және карта нөмірін жібермеңіз. Жеке деректерді алдын ала жабыңыз. "
    "Шифрланған сессия 30 минутқа дейін сақталады. /delete белсенді деректерді жояды; Telegram, "
    "провайдер және бұрынғы сақтық көшірмелердегі деректерді жоймайды. Өңдеу үшін «Келісемін» таңдаңыз."
)
URGENT = (
    ("Если сейчас списывают деньги или вы передали доступ: прекратите контакт, свяжитесь с банком через "
     "официальный канал и попросите защитить доступ и операции. Сохраните доказательства. Не делайте новых переводов."),
    ("Ақша алынып жатса немесе қолжетімділік берсеңіз: байланысты тоқтатыңыз, банктің ресми арнасы арқылы "
     "қолжетімділік пен операцияларды қорғауды сұраңыз. Дәлелдерді сақтаңыз. Жаңа аударым жасамаңыз."))
HELP_TEXT = (
    "/check — проверка / тексеру\n/help_mode — помощь / көмек\n"
    "/confirm — подтвердить анкету / сауалнаманы растау\n/skip — неизвестно / белгісіз\n"
    "/reset — новая анкета / жаңа сауалнама\n/analyze — анализ анкеты / сауалнаманы талдау\n"
    "/stop — остановить анкету / сауалнаманы тоқтату\n/resume — продолжить анкету / жалғастыру\n"
    "/audio_off — отключить расшифровку / аудионы өңдеуді өшіру\n"
    "/document police pdf — заявление / арыз\n"
    "Виды / Түрлері: police, bank_dispute, bank_loan, regulator, block_reason, restructure, evidence\n"
    "Форматы / Пішімдер: pdf, docx, txt\n/web_on, /web_off — поиск / іздеу\n/delete — удалить / жою")


class Controller:
    def __init__(self, bot, store, assistant, config):
        self.bot, self.store, self.assistant, self.cfg = bot, store, assistant, config

    async def handle(self, row):
        update = Update.model_validate(self.store.open(row["payload"]), context={"bot": self.bot})
        message = update.message
        s = await self.store.get(row["session_id"])
        text = message.text or message.caption or ""
        kk = s.language == "kk"

        async def send(body, markup=None):
            for start in range(0, len(body), 3500):
                if not await self.store.active(row["update_id"]) or s.expires <= time.time():
                    raise asyncio.CancelledError
                if start:
                    await asyncio.sleep(1.1)
                await message.answer(body[start:start+3500], reply_markup=markup, parse_mode=None, disable_web_page_preview=True)

        async def save():
            if await self.store.active(row["update_id"]):
                await self.store.save(row["session_id"], s)

        if text in {"Русский", "Қазақша"}:
            s.language = "kk" if text == "Қазақша" else "ru"
            await save()
            await send("Тіл: қазақша." if s.language == "kk" else "Язык: русский.", MENU)
            return
        if text == "Согласен / Келісемін":
            s.consent = True
            await save()
            await send("Режимді таңдаңыз." if kk else "Выберите режим.", MENU)
            return
        if not s.consent:
            await send(NOTICE, MENU)
            return
        if text == "/help":
            await send(HELP_TEXT, MENU)
            return
        if text in {AUDIO_CONSENT, "/audio_off"}:
            s.audio_consent = text == AUDIO_CONSENT
            await save()
            await send(("Аудионы жіберіңіз." if kk else "Отправьте аудиозапись.") if s.audio_consent else
                       ("Аудионы өңдеу өшірілді." if kk else "Расшифровка аудио отключена."), MENU)
            return
        if text in {"/web_on", "/web_off"}:
            s.web_consent = text == "/web_on"
            await save()
            enabled = s.web_consent and self.cfg.enable_web_search
            await send(("Іздеу қосылды." if enabled else "Іздеу өшірілді.") if kk else
                       ("Поиск включён." if enabled else "Поиск выключен."))
            return
        if text == "Юрист / Заңгер":
            await send(self.cfg.consultation_url or ("Байланыс әлі орнатылмаған." if kk else "Контакт консультации ещё не настроен."))
            return
        if text in {"Проверь / Тексер", "/check", "Уже случилось / Болып қойды", "/help_mode", "/reset"}:
            s.mode = "check" if text in {"Проверь / Тексер", "/check"} else "help"
            s.case, s.history = {}, []
            s.case_paused = False
            await save()
            await send(("Хабарлама не файл жіберіңіз." if kk else "Пришлите сообщение или файл.") if s.mode == "check" else URGENT[kk],
                       MENU if s.mode == "check" else HELP_MENU)
            return
        if text in BRANCH_BUTTONS:
            case = Case(branch=BRANCH_BUTTONS[text])
            s.mode, s.case, s.history = "help", case.model_dump(), []
            s.case_paused = False
            await save()
            await send(case.question(s.language), MENU)
            return
        case = Case.model_validate(s.case or {})
        if text == "/stop":
            s.case_paused = True
            await save()
            await send("Сауалнама тоқтатылды." if kk else "Анкета остановлена. Можете описать другую ситуацию.")
            return
        if text == "/resume":
            if not case.branch:
                await send("Алдымен жағдайды таңдаңыз." if kk else "Сохранённой анкеты нет. Выберите ситуацию.", HELP_MENU)
                return
            s.case_paused, s.history = False, []
            await save()
            await send(case.question(s.language) or case.summary(s.language))
            return
        if text == "/confirm":
            if s.case_paused or case.next_field() or not case.branch:
                await send("Сауалнама дайын емес. /resume — жалғастыру." if kk else
                           "Анкета не завершена или приостановлена. /resume — продолжить.")
                return
            case.confirm()
            s.case = case.model_dump()
            await save()
            await send("Расталды. /analyze — жоспар; /document police pdf — арыз." if kk else
                       "Факты подтверждены. /analyze — план; /document police pdf — заявление. Другие виды: /help")
            return
        if text.startswith("/document"):
            parts = text.split()
            kind, fmt = (parts[1] if len(parts) > 1 else "police"), (parts[2] if len(parts) > 2 else "pdf")
            if not case.confirmed or s.case_paused:
                await send("Сауалнаманы толтырып, /confirm жіберіңіз." if kk else "Заполните анкету в режиме помощи и подтвердите /confirm.", HELP_MENU)
                return
            if kind not in TITLES or fmt not in {"pdf", "docx", "txt"}:
                await send(HELP_TEXT)
                return
            data = await asyncio.to_thread(export, build_draft(kind, case, s.language), fmt, self.cfg.font_path)
            if await self.store.active(row["update_id"]):
                await message.answer_document(BufferedInputFile(data, filename=f"zan-{kind}.{fmt}"),
                    caption="Жоба. Жібермес бұрын тексеріңіз." if kk else "Черновик. Проверьте факты и заполните поля перед подачей.")
            return
        if case.next_field() and not s.case_paused and text == "/skip":
            case.record("Белгісіз" if kk else "Неизвестно")
            s.case = case.model_dump()
            await save()
            await send(case.question(s.language) or case.summary(s.language) +
                       ("\n\n/confirm — растау; /reset — қайта толтыру" if kk else
                        "\n\n/confirm — подтвердить; /reset — заполнить заново"))
            return
        if text == "/analyze":
            if not case.confirmed or s.case_paused:
                await send("Алдымен /confirm." if kk else "Сначала подтвердите анкету: /confirm.")
                return
            text = case.summary(s.language)
        elif text.startswith("/"):
            await send(HELP_TEXT)
            return
        if not await self.store.quota(row["session_id"], self.cfg.daily_request_limit):
            await send("Бүгінгі сұраулар шегіне жеттіңіз." if kk else "Достигнут дневной лимит анализа. Попробуйте завтра.")
            return
        image = None
        audio = audio_attachment(message)
        if audio:
            if not s.audio_consent:
                await send("Жазба сыртқы ЖИ сервисіне жіберіледі. Келіссеңіз, түймені басып, аудионы қайта жіберіңіз."
                           if kk else "Для расшифровки запись будет отправлена внешнему ИИ. "
                           "Если согласны, нажмите кнопку и отправьте аудио повторно.", keyboard([[AUDIO_CONSENT]]))
                return
            recording, filename = audio
            if (recording.file_size is None or recording.file_size > self.cfg.max_file_bytes or
                    getattr(recording, "duration", 0) > self.cfg.max_audio_seconds):
                await send("Аудио тым үлкен не ұзақ. Қысқа үзінді жіберіңіз." if kk else
                           "Запись слишком большая или длинная. Отправьте короткий фрагмент: до 5 минут и 10 МБ.")
                return
            output = io.BytesIO()
            await self.bot.download(recording.file_id, destination=output, timeout=30)
            await send("Аудио мәтінге айналдырылуда." if kk else "Расшифровываю аудиозапись.")
            transcript = await self.assistant.transcribe(filename, output.getvalue())
            text += "\n" + transcript
            await send(("Танылған мәтін. Қате болса, түзетіңіз:\n" if kk else
                        "Распознанный текст. Если есть ошибки, уточните их:\n") + transcript)
        file = None if audio else message.document or (message.photo[-1] if message.photo else None)
        if file:
            if file.file_size is None or file.file_size > self.cfg.max_file_bytes:
                raise ValueError("File size")
            output = io.BytesIO()
            await self.bot.download(file.file_id, destination=output, timeout=30)
            extracted = await extract(getattr(file, "file_name", None) or "photo.jpg", output.getvalue())
            text += "\n" + extracted["text"]
            image = extracted["image"]
            await send("Мәтінде қате болуы мүмкін. Сома мен күндерді растаңыз." if kk else
                       "В извлечённом тексте возможны ошибки. Суммы и даты подтвердите в анкете перед документом.")
        if not text.strip() and not image:
            await send("Мәтін, құжат, сурет не аудио жіберіңіз." if kk else "Отправьте текст, документ, изображение или аудиозапись.")
            return
        if len(text) > self.cfg.max_input_chars:
            await send("Қысқа үзінді жіберіңіз." if kk else "Сообщение слишком длинное. Отправьте короткий фрагмент.")
            return
        if message.text != "/analyze":
            turn = await self.assistant.dialogue(text, s.language, case.model_dump(), s.case_paused,
                                                case.question(s.language), s.history, image)
            if turn.action == "answer" and case.next_field() and not s.case_paused and not image:
                if len(text) > 3000:
                    await send("Жауапты қысқартыңыз." if kk else "Сократите ответ для анкеты до 3000 символов.")
                    return
                case.record(redact(text))
                s.case = case.model_dump()
                await save()
                await send(case.question(s.language) or case.summary(s.language) +
                           ("\n/confirm — растау" if kk else "\n/confirm — подтвердить; /reset — заполнить заново"))
                return
            if turn.action in {"pause", "off_topic", "clarify"}:
                if turn.action != "clarify":
                    s.case_paused = True
                reply = turn.reply.strip() or ("Нақтылап жазыңыз." if kk else "Уточните, с чем нужна помощь.")
                s.history = (s.history + [redact(text), "[Assistant] " + reply])[-8:]
                await save()
                await send(reply)
                return
            if turn.action == "new_topic":
                s.history = []
                s.mode = "help"
            elif case.branch and not s.case_paused:
                s.history = [case.summary(s.language)]
            if case.branch:
                s.case_paused = True
            # Persist the pause before analysis; an LLM failure must not resume the old questionnaire.
            await save()
        combined = "\n".join(s.history + [redact(text)])
        if len(combined) > self.cfg.max_input_chars:
            await send("Мәтін тым ұзақ. /reset не қысқа үзінді жіберіңіз." if kk else "Текст слишком длинный. Начните /reset или отправьте короткий фрагмент.")
            return
        await send("Белгілер мен дереккөздер тексерілуде." if kk else "Проверяю признаки и источники.")
        answer, sources = await self.assistant.analyze(combined, s.mode, s.language, s.web_consent, image)
        s.history.append(redact(text) + ("\n" + redact(answer.summary) if image else ""))
        if answer.questions:
            s.history.append("[Assistant questions] " + " / ".join(answer.questions))
        await save()
        await send(render(answer, sources))


async def run():
    cfg = settings()
    cfg.validate_bot()
    await migrate_database(cfg.database_url)
    pool = await asyncpg.create_pool(cfg.database_url, min_size=1, max_size=10)
    store = PrivateStore(pool, cfg.data_encryption_key, cfg.session_ttl_seconds, cfg.max_queue_jobs)
    assistant = Assistant(cfg, pool)
    bot = Bot(cfg.telegram_bot_token)
    controller = Controller(bot, store, assistant, cfg)
    active = {}
    leader = await asyncpg.connect(cfg.database_url)
    lock = int.from_bytes(hashlib.sha256(cfg.telegram_bot_token.encode()).digest()[:8], "big", signed=True)
    await leader.execute("SELECT pg_advisory_lock($1)", lock)
    await pool.execute("UPDATE bot_jobs SET lease_until=now() WHERE status='running'")

    async def incoming(message: Message, event_update: Update):
        if message.chat.type != "private" or not message.from_user:
            return
        key = session_key(message.from_user.id, cfg.session_secret)
        text = message.text or ""
        if text == "/start":
            await message.answer(NOTICE, reply_markup=MENU)
            return
        if text == "/delete":
            task = active.get(key)
            if task:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            await store.delete(key)
            await message.answer("Активная сессия и очередь удалены.\nБелсенді сессия мен кезек жойылды.")
            return
        s = await store.get(key)
        if not s.consent and text not in {"Согласен / Келісемін", "Русский", "Қазақша"}:
            await message.answer(NOTICE, reply_markup=MENU)
            return
        payload = {"update_id": event_update.update_id, "message": {
            "message_id": message.message_id, "date": int(message.date.timestamp()),
            "chat": {"id": message.chat.id, "type": "private"},
            "from": {"id": message.from_user.id, "is_bot": False, "first_name": "User"},
            "text": message.text, "caption": message.caption,
            "document": message.document.model_dump(mode="json") if message.document else None,
            "voice": message.voice.model_dump(mode="json") if message.voice else None,
            "audio": message.audio.model_dump(mode="json") if message.audio else None,
            "photo": [p.model_dump(mode="json") for p in message.photo] if message.photo else None}}
        if not await store.enqueue(event_update.update_id, key, payload):
            await message.answer("Очередь заполнена. Попробуйте позже.\nКезек толы. Кейінірек көріңіз.")

    async def worker():
        while True:
            row = await store.claim()
            if row is None:
                await asyncio.sleep(0.5)
                continue
            task = asyncio.create_task(controller.handle(row))
            active[row["session_id"]] = task
            success = False
            try:
                await asyncio.wait_for(task, timeout=210)
                success = True
            except asyncio.CancelledError:
                if asyncio.current_task().cancelling():
                    raise
            except Exception as exc:  # noqa: BLE001 -- log type only, never provider payload
                log.warning("job_failed type=%s", type(exc).__name__)
                if await store.active(row["update_id"]):
                    raw = store.open(row["payload"])
                    await bot.send_message(raw["message"]["chat"]["id"],
                        "Не удалось завершить обработку. Это не означает низкий риск. Проверьте формат/размер или повторите позже.\n"
                        "Өңдеу аяқталмады. Бұл тәуекел төмен дегенді білдірмейді. Файлды тексеріңіз не кейінірек қайталаңыз.")
            finally:
                active.pop(row["session_id"], None)
                if not asyncio.current_task().cancelling():
                    await store.finish(row["update_id"], success)

    async def cleanup():
        while True:
            await store.purge()
            await leader.fetchval("SELECT 1")
            await asyncio.sleep(10)

    async def poll():
        # Advance Telegram offset only after durable enqueue succeeds.
        offset = None
        connected = False
        while True:
            try:
                updates = await bot.get_updates(offset=offset, timeout=30, allowed_updates=["message"])
                if not connected:
                    print("Telegram polling connected", flush=True)
                    connected = True
                for update in updates:
                    if update.message:
                        await incoming(update.message, update)
                    offset = update.update_id + 1
            except Exception as exc:  # noqa: BLE001 -- retain offset and avoid logging tokens/payloads
                log.warning("poll_retry type=%s", type(exc).__name__)
                await asyncio.sleep(2)

    stop = asyncio.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        try:
            asyncio.get_running_loop().add_signal_handler(signum, stop.set)
        except NotImplementedError:
            pass  # Windows asyncio.Runner still handles KeyboardInterrupt.

    tasks = [asyncio.create_task(worker()) for _ in range(cfg.max_concurrent_requests)]
    tasks += [asyncio.create_task(cleanup()), asyncio.create_task(poll()), asyncio.create_task(stop.wait())]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await assistant.client.close()
        await bot.session.close()
        await leader.close()
        await pool.close()


if __name__ == "__main__":
    asyncio.run(run())
