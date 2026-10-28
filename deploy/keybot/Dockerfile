# Telegram-бот выдачи ключей neurogate (neurogate bot, режим webhook).
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev && useradd -r -u 1000 bot && mkdir -p /data && chown bot /data
USER bot
ENV BOT_DB=/data/keybot.db BOT_HOST=0.0.0.0 BOT_PORT=8080 TELEGRAM_MODE=webhook PYTHONUNBUFFERED=1
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')"
CMD ["/app/.venv/bin/neurogate", "bot"]
