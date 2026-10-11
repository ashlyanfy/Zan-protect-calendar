# Zan Protect bot

Telegram-помощник по мошенничеству в Казахстане. Python 3.11, aiogram, FastAPI, PostgreSQL, внешний LLM.
Версия **0.2**. Техническая реализация расширена; публичный выпуск зависит от проверенной правовой базы,
экспертной оценки, настройки внешних сервисов и мер обработки файлов/персональных данных.

## Что работает в коде

- «Проверь» и «Уже случилось», RU/KK, пять последовательных анкет и подтверждение фактов.
- Семь видов черновиков: полиция, спорная операция, спорный кредит, АРРФР, основания блокировки,
  временные меры по займу, памятка доказательств. Выдача PDF/DOCX/TXT без генерации вымышленных фактов.
- Извлечение PDF/DOCX/PPTX/XLSX/текста, изображения и OCR PDF-сканов через Tesseract.
- Поиск по словам + смыслу, проверка актуальности/публикации источников, отдельный verifier ответа.
- Опциональный web search по фиксированной теме с согласием. Пользовательские URL не скачиваются.
- Зашифрованные PostgreSQL-сессии и очередь, TTL, отмена /delete, квоты, дедупликация update_id и leader lock.
- Редакционный API с отдельным ключом, импорт/публикация/отзыв и журнал действий.
- Railway Docker, миграции, health/readiness, тесты и скрипт реальной оценки модели.

## Главные документы

- [Фактический статус 0.2 и ограничения](docs/RELEASE_02.md)
- [Какие ресурсы и данные нужны](docs/DATA_REQUIREMENTS.md)
- [Пошаговый деплой Railway](docs/RAILWAY.md)
- [Результаты проверок](docs/VALIDATION.md)
- [База знаний](docs/KNOWLEDGE.md) · [Промпты](prompts/) · [Источники-кандидаты](data/resources.json)

## Настройка

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Заполнить `.env`: токен Telegram, API-ключ LLM, модель с нужными возможностями, URL PostgreSQL,
API_SECRET, SESSION_SECRET, ADMIN_SECRET и DATA_ENCRYPTION_KEY. Не отправлять ключи в чат или Git.
API_SECRET/SESSION_SECRET/ADMIN_SECRET — разные случайные значения длиной от 32 символов.

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Вторая команда — DATA_ENCRYPTION_KEY; сохранять между перезапусками. Для локальной БД POSTGRES_PASSWORD
должен совпадать с паролем DATABASE_URL. Docker Compose запускает только БД:

```powershell
docker compose up -d postgres
.\.venv\Scripts\python.exe -m scripts.migrate
.\.venv\Scripts\python.exe -m scripts.seed
.\.venv\Scripts\python.exe -m app.bot
```

OCR на Windows требует установленного Tesseract с rus/kaz/eng на PATH. В Docker эти зависимости включены.
Для PDF нужен Unicode TTF: Windows Arial либо Linux DejaVu Sans (устанавливается Dockerfile).
При необходимости путь задаётся FONT_PATH. Основной запуск на Railway описан в docs/RAILWAY.md.

## Пользовательский путь

`/start` → согласие → язык → режим. «Проверь»: сообщение/файл → риск, признаки и доступные источники.
«Уже случилось»: срочная памятка → выбор одной из пяти ситуаций → вопросы по одному → сводка → `/confirm`.
После подтверждения: `/analyze` для плана, `/document police pdf` для заявления.

Виды документов: `police`, `bank_dispute`, `bank_loan`, `regulator`, `block_reason`, `restructure`, `evidence`.
Форматы: `pdf`, `docx`, `txt`. `/skip` отмечает неизвестный ответ, `/reset` начинает анкету заново.
`/delete` отменяет задачу и удаляет активный серверный контекст. `/web_on` и `/web_off` управляют согласием
на внешний поиск; оператор также должен включить ENABLE_WEB_SEARCH. `/help` показывает команды.

## База знаний и редактура

Поставляются 3 синтетические draft-карточки. Проверенных правовых фрагментов пока нет.
Публикация не происходит автоматически ни после импорта, ни после поиска в интернете.

```powershell
.\.venv\Scripts\python.exe -m scripts.export_schemas
.\.venv\Scripts\python.exe -m scripts.knowledge validate --kind scheme --file data/schemes.seed.json
.\.venv\Scripts\python.exe -m scripts.knowledge import --kind scheme --file data/schemes.seed.json
.\.venv\Scripts\python.exe -m scripts.knowledge index
```

`index` делает платные embedding-вызовы только для опубликованных материалов. После публикации новых
материалов повторить index. Для норм `--kind legal`; поля описаны в `data/schemas/legal.schema.json`.
Редактор проверяет источник, сроки, применимость и язык перед публикацией.

## API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --no-access-log
```

- `/health`, `/ready`: состояние сервиса и БД.
- `POST /v1/analyze`: text, mode, language, web_consent; X-API-Key.
- `POST /v1/documents/export`: kind, language, branch, facts, confirmed, format; X-API-Key.
- `POST /admin/legal`, `/admin/schemes`: импорт draft; X-Admin-Key.
- `POST /admin/{legal|scheme}/{id}/publish`: reviewer, publish; X-Admin-Key.
- `GET /admin/status`: агрегаты корпуса и очереди; X-Admin-Key.

Схемы доступны на `/docs`. Общие служебные ключи нельзя встраивать в публичный браузерный frontend.
Admin API — для одного доверенного оператора, не замена персональным ролям большой редакции.

## Проверка

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app scripts tests
```

Для интеграционных тестов нужна отдельная локальная база с именем `zan_test` и переменная
ZAN_TEST_DATABASE_URL. Тесты очищают только таблицы этой тестовой базы и отклоняют URL production.
LLM-eval запускается отдельно: `python -m scripts.evaluate data/eval.seed.jsonl`; он расходует API-бюджет.
Шесть учебных eval-ситуаций не заменяют полноценный независимый набор с экспертной оценкой.

## Границы

Файлы до 10 МБ и 24 000 извлечённых символов; PDF-текст до 40 страниц, OCR до 10 страниц.
Не все вложенные изображения, формулы и элементы Office извлекаются. Старые DOC/PPT/XLS, архивы,
аудио/видео не поддерживаются. Парсер не является полной антивирусной песочницей.

Правовая база и шаблоны требуют содержательной проверки юристом. Качество реального LLM ещё не измерено
без пользовательских ключей. Отсутствие источников не считается низким риском. Веб-справка не становится нормой.
TTL не удаляет историю Telegram, provider retention и резервные копии. При аварии после отправки ответа
возможен повтор сообщения. Все остальные ограничения и условия публичного запуска — RELEASE_02.md.
