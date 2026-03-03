FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN useradd -m -u 1000 app
WORKDIR /app

COPY services/brain/requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY shared/ /app/shared/
COPY services/brain/ /app/services/brain/

USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import httpx; r=httpx.get('http://localhost:8000/health'); exit(0 if r.status_code==200 else 1)"

CMD ["uvicorn", "services.brain.streaming:app", "--host", "0.0.0.0", "--port", "8000"]
