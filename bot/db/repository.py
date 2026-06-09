"""
bot/db/repository.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — Stage 6: Async Data Access Layer
══════════════════════════════════════════════════════════════════════════════
All DB interactions go through this module.
Uses aiosqlite in WAL mode for concurrent async reads.

Stage 6 additions
──────────────────
  get_user_history()         — paginated /history for a user (last N requests)
  get_request_by_id()        — /status <id>  (exact ID lookup)
  get_latest_request()       — /status with no args (most recent)
  update_request_decision()  — now persists suggested_alternative, grade, rag_signal
  log_security_event()       — persists raw_points alongside signals
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

import aiosqlite
import structlog

from bot.config import get_settings

log      = structlog.get_logger(__name__)
settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Connection helper
# ─────────────────────────────────────────────────────────────────────────────

def _db() -> aiosqlite.Connection:
    return aiosqlite.connect(str(settings.db_path))


# ─────────────────────────────────────────────────────────────────────────────
# Sessions
# ─────────────────────────────────────────────────────────────────────────────

async def upsert_session(user_id: int, state: str = "COLLECTING") -> int:
    """Create a new session for user; return its ID."""
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
            "UPDATE sessions SET state='CANCELLED', updated_at=datetime('now') WHERE id=?",
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
    """Persist a new PENDING asset request. Returns the 8-char uppercase UUID."""
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
    policy_refs: Optional[List[str]] = None,
    suggested_alternative: Optional[str] = None,
    employee_grade: Optional[str] = None,
    rag_signal: Optional[str] = None,
) -> None:
    """Write the decision engine outcome back to the request row."""
    async with _db() as db:
        await db.execute(
            """UPDATE asset_requests
               SET status=?, decision_reason=?, policy_refs=?,
                   suggested_alternative=?, employee_grade=?, rag_signal=?,
                   updated_at=datetime('now')
               WHERE id=?""",
            (
                status,
                reason,
                json.dumps(policy_refs or []),
                suggested_alternative,
                employee_grade,
                rag_signal,
                request_id,
            ),
        )
        await db.commit()


async def get_request_by_id(request_id: str) -> Optional[Dict[str, Any]]:
    """/status <id> — exact match by short ID."""
    async with _db() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM asset_requests WHERE id=?",
            (request_id.upper(),),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_latest_request(user_id: int) -> Optional[Dict[str, Any]]:
    """/status with no args — most recent request for this user."""
    async with _db() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM asset_requests WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_user_history(
    user_id: int,
    limit: int = 10,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    /history — paginated list of a user's requests, newest first.
    Returns up to `limit` rows starting at `offset`.
    """
    async with _db() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT id, asset_name, status, urgency, cost_estimate,
                      suggested_alternative, created_at, updated_at
               FROM asset_requests
               WHERE user_id=?
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (user_id, limit, offset),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Security Events
# ─────────────────────────────────────────────────────────────────────────────

async def log_security_event(
    user_id: int,
    event_type: str,
    score: float,
    signals: Dict[str, Any],
    snippet: str = "",
    raw_points: int = 0,
) -> None:
    async with _db() as db:
        await db.execute(
            """INSERT INTO security_events
               (user_id, event_type, score, raw_points, signals, snippet)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, event_type, score, raw_points, json.dumps(signals), snippet[:500]),
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
            "INSERT INTO audit_log (request_id, actor, action, detail) VALUES (?,?,?,?)",
            (request_id, actor, action, detail),
        )
        await db.commit()
