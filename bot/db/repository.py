"""
bot/db/repository.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — Async Data Access Layer
══════════════════════════════════════════════════════════════════════════════
All database interactions go through this module.
Uses aiosqlite with WAL mode for concurrent reads.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

import aiosqlite
import structlog

from bot.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Connection helper
# ─────────────────────────────────────────────────────────────────────────────

def _db() -> aiosqlite.Connection:
    return aiosqlite.connect(settings.db_path)


# ─────────────────────────────────────────────────────────────────────────────
# Sessions
# ─────────────────────────────────────────────────────────────────────────────

async def upsert_session(user_id: int, state: str = "COLLECTING") -> int:
    """Create or reset a session for user; return session ID."""
    async with _db() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "INSERT INTO sessions (user_id, state) VALUES (?, ?) RETURNING id",
            (user_id, state),
        )
        row = await cur.fetchone()
        await db.commit()
        return row["id"]


async def cancel_session(session_id: int) -> None:
    async with _db() as db:
        await db.execute(
            "UPDATE sessions SET state = 'CANCELLED', updated_at = datetime('now') WHERE id = ?",
            (session_id,),
        )
        await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Asset Requests
# ─────────────────────────────────────────────────────────────────────────────

async def create_request(
    session_id: int,
    user_id: int,
    slots: Dict[str, Any],
) -> str:
    """Persist a new asset request; return its UUID."""
    req_id = str(uuid.uuid4())[:8].upper()
    async with _db() as db:
        await db.execute(
            """INSERT INTO asset_requests
               (id, session_id, user_id, asset_name, asset_category,
                justification, urgency, cost_estimate, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')""",
            (
                req_id,
                session_id,
                user_id,
                slots.get("asset_name"),
                slots.get("asset_category"),
                slots.get("justification"),
                slots.get("urgency", "NORMAL"),
                slots.get("cost_estimate"),
            ),
        )
        await db.commit()
    log.info("request_created", req_id=req_id, user_id=user_id)
    return req_id


async def update_request_decision(
    request_id: str,
    status: str,
    reason: str,
    policy_refs: list[str] | None = None,
) -> None:
    async with _db() as db:
        await db.execute(
            """UPDATE asset_requests
               SET status = ?, decision_reason = ?, policy_refs = ?,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (status, reason, json.dumps(policy_refs or []), request_id),
        )
        await db.commit()


async def get_request_by_id(request_id: str) -> Optional[Dict[str, Any]]:
    async with _db() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM asset_requests WHERE id = ?", (request_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_latest_request(user_id: int) -> Optional[Dict[str, Any]]:
    async with _db() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM asset_requests WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


# ─────────────────────────────────────────────────────────────────────────────
# Security Events
# ─────────────────────────────────────────────────────────────────────────────

async def log_security_event(
    user_id: int,
    event_type: str,
    score: float,
    signals: Dict[str, float],
    snippet: str = "",
) -> None:
    async with _db() as db:
        await db.execute(
            """INSERT INTO security_events (user_id, event_type, score, signals, snippet)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, event_type, score, json.dumps(signals), snippet[:500]),
        )
        await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Audit Log
# ─────────────────────────────────────────────────────────────────────────────

async def append_audit(
    request_id: str,
    actor: str,
    action: str,
    detail: str = "",
) -> None:
    async with _db() as db:
        await db.execute(
            "INSERT INTO audit_log (request_id, actor, action, detail) VALUES (?, ?, ?, ?)",
            (request_id, actor, action, detail),
        )
        await db.commit()
