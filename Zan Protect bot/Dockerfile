FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core tesseract-ocr tesseract-ocr-rus tesseract-ocr-kaz \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-runtime.txt ./
RUN pip install -r requirements-runtime.txt && useradd --create-home --uid 10001 zan

COPY app/ ./app/
COPY prompts/ ./prompts/
COPY sql/ ./sql/
COPY scripts/ ./scripts/
COPY data/ ./data/

USER zan
CMD ["python", "-m", "app.bot"]
