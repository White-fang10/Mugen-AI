# ─────────────────────────────────────────────────────────────────────────────
# MUGEN AI — SD-05 Simplified Dockerfile
# Telegram bot only. No admin panel. No ChromaDB. No heavy ML models.
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Prevent .pyc files and enable unbuffered stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ── Python dependencies (much lighter now) ────────────────────────────────────
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

# ── Ensure data directory exists for SQLite ───────────────────────────────────
RUN mkdir -p /app/data

# ── Non-root user (security hardening) ───────────────────────────────────────
RUN useradd -m -u 1001 mugen && chown -R mugen:mugen /app
USER mugen

# ── Healthcheck ───────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "from bot.config import get_settings; get_settings()" || exit 1

# ── Run the startup script ────────────────────────────────────────────────────
RUN chmod +x /app/start.sh
CMD ["/app/start.sh"]
