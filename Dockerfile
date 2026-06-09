# ─────────────────────────────────────────────────────────────────────────────
# MUGEN AI — Dockerfile (Railway / Docker deployment ready)
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Prevent .pyc files and enable unbuffered stdout (critical for logging)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ── System dependencies ───────────────────────────────────────────────────────
# libmupdf and libgl are required by PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libmupdf-dev \
        mupdf-tools \
        libgl1-mesa-glx \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Pre-download the sentence-transformer model at build time (avoids cold-start)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

# ── Persistent volumes ────────────────────────────────────────────────────────
VOLUME ["/app/chroma_store", "/app/data", "/app/rulebooks"]

# ── Non-root user (security hardening) ───────────────────────────────────────
RUN useradd -m -u 1001 mugen && chown -R mugen:mugen /app
USER mugen

# ── Healthcheck ───────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import bot.config; bot.config.get_settings()" || exit 1

# ── Entrypoint ────────────────────────────────────────────────────────────────
CMD ["python", "-m", "bot.main"]
