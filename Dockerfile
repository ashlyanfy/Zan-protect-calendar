# --- Сборка фронтенда ---
FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Бэкенд + статика ---
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend /build/dist ./frontend/dist

# main.py ищет frontend/dist на два уровня выше пакета app
ENV PYTHONUNBUFFERED=1
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
