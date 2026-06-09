"""
bot/db/schema.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — SQLite Schema & Initialisation
══════════════════════════════════════════════════════════════════════════════
Tables
  sessions        — Active conversation sessions
  asset_requests  — Completed/in-flight asset requests
  security_events — Quarantine and anomaly log
  audit_log       — Append-only decision audit trail
"""

from __future__ import annotations

import aiosqlite
import structlog

from bot.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

_DDL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    state       TEXT    NOT NULL DEFAULT 'COLLECTING',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS asset_requests (
    id              TEXT PRIMARY KEY,
    session_id      INTEGER REFERENCES sessions(id),
    user_id         INTEGER NOT NULL,
    asset_name      TEXT,
    asset_category  TEXT,
    justification   TEXT,
    urgency         TEXT,
    cost_estimate   REAL,
    status          TEXT NOT NULL DEFAULT 'PENDING',
    decision_reason TEXT,
    policy_refs     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS security_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    event_type  TEXT    NOT NULL,
    score       REAL    NOT NULL,
    signals     TEXT    NOT NULL,
    snippet     TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id  TEXT,
    actor       TEXT    NOT NULL,
    action      TEXT    NOT NULL,
    detail      TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sessions_user    ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_requests_user    ON asset_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_security_user    ON security_events(user_id);
"""


async def init_db() -> None:
    """Create all tables (idempotent)."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.executescript(_DDL)
        await db.commit()
    log.info("db_schema_initialised", path=str(settings.db_path))
