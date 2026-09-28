# ZanProtect Календарь

Персональный календарь судебных заседаний и юридических событий. PWA (устанавливается на телефон), React + TypeScript + FastAPI + PostgreSQL.

## Локальный запуск

**Бэкенд** (порт 8000, локально использует SQLite `backend/zanprotect.db`):

```bash
cd backend
.venv/Scripts/uvicorn app.main:app --reload --port 8000
```

**Фронтенд** (порт 5173, проксирует `/api` на бэкенд):

```bash
cd frontend
npm run dev
```

Открыть: http://localhost:5173

## Деплой на Railway

1. Запушить репозиторий на GitHub и создать проект в Railway из этого репо — `Dockerfile` и `railway.json` подхватятся автоматически.
2. Добавить в проект плагин **PostgreSQL** — Railway сам передаст `DATABASE_URL` сервису (если нет, добавить переменную `DATABASE_URL = ${{Postgres.DATABASE_URL}}`).
3. Открыть выданный домен — фронтенд и API работают с одного сервиса.

Переменные окружения:

| Переменная | Описание |
| --- | --- |
| `DATABASE_URL` | PostgreSQL URL (Railway подставляет сам). Без неё — SQLite для локальной разработки |
| `CORS_ORIGINS` | Список разрешённых origin через запятую (нужно только если фронт хостится отдельно) |

## Структура

- `backend/` — FastAPI, SQLAlchemy 2.0, Pydantic v2. CRUD `/api/events`, healthcheck `/api/health`
- `frontend/` — Vite + React + TS, PWA (vite-plugin-pwa), режимы День/Неделя/Месяц, напоминания через браузерные уведомления
- `Dockerfile` — multi-stage сборка: фронтенд собирается и раздаётся FastAPI со того же домена
