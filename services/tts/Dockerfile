FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends --fix-missing \
    libsndfile1 ffmpeg \
    || (apt-get update && apt-get install -y --no-install-recommends --fix-missing \
    libsndfile1 ffmpeg) \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN useradd -m -u 1000 app
WORKDIR /app

COPY services/tts/requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY shared/ /app/shared/
COPY services/tts/ /app/services/tts/

RUN mkdir -p /models /voices && chown -R app:app /models /voices
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import httpx; r=httpx.get('http://localhost:8000/health'); exit(0 if r.status_code==200 else 1)"

CMD ["uvicorn", "services.tts.streaming:app", "--host", "0.0.0.0", "--port", "8000"]
