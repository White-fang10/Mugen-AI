"""
bot/db/schema.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — Stage 6: SQLite Schema (WAL mode)
══════════════════════════════════════════════════════════════════════════════
Tables
  sessions          — Active conversation sessions
  asset_requests    — All requests (PENDING → APPROVED/FLAGGED/REJECTED/CANCELLED)
  security_events   — Quarantine + flag events (audit trail)
  audit_log         — Append-only decision ledger

Stage 6 additions
  asset_requests.suggested_alternative  — filled when decision engine suggests one
  asset_requests.employee_grade         — grade at time of request (immutable snapshot)
  asset_requests.rag_signal             — STRONG/WEAK/NONE from retrieval
  Indexes for /status and /history query paths
"""

from __future__ import annotations

import aiosqlite
import structlog

from bot.config import get_settings

log      = structlog.get_logger(__name__)
settings = get_settings()

_DDL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA synchronous  = NORMAL;

-- ── Sessions ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    state       TEXT    NOT NULL DEFAULT 'COLLECTING',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Asset Requests ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS asset_requests (
    id                    TEXT PRIMARY KEY,
    session_id            INTEGER REFERENCES sessions(id),
    user_id               INTEGER NOT NULL,
    asset_name            TEXT,
    asset_category        TEXT,
    justification         TEXT,
    urgency               TEXT,
    cost_estimate         REAL,
    status                TEXT    NOT NULL DEFAULT 'PENDING',
    decision_reason       TEXT,
    policy_refs           TEXT,              -- JSON array
    suggested_alternative TEXT,              -- Stage 6: best alternative product
    employee_grade        TEXT,              -- Stage 6: grade snapshot at request time
    rag_signal            TEXT,              -- Stage 6: STRONG | WEAK | NONE
    created_at            TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at            TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Security Events ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS security_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    event_type  TEXT    NOT NULL,     -- QUARANTINE | FLAG | INJECTION_FREEZE
    score       REAL    NOT NULL,
    raw_points  INTEGER NOT NULL DEFAULT 0,
    signals     TEXT    NOT NULL,     -- JSON object
    snippet     TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Audit Log (append-only) ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id  TEXT,
    actor       TEXT    NOT NULL,
    action      TEXT    NOT NULL,
    detail      TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Indexes ────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_sessions_user    ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_requests_user    ON asset_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_requests_status  ON asset_requests(status);
CREATE INDEX IF NOT EXISTS idx_requests_created ON asset_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_security_user    ON security_events(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_request    ON audit_log(request_id);
"""


async def init_db() -> None:
    """Create all tables and indexes (idempotent — safe to call on every boot)."""
    async with aiosqlite.connect(str(settings.db_path)) as db:
        await db.executescript(_DDL)
        await db.commit()
    log.info("db_schema_initialised", path=str(settings.db_path))
