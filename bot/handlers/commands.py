"""
bot/handlers/commands.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — Command Handlers
══════════════════════════════════════════════════════════════════════════════
Implements:
  /start    — Welcome & capability overview
  /status   — Rich MARKDOWN_V2 request card
  /history  — Last 10 requests with inline summaries
  /cancel   — Abort in-progress conversation

Note: Rulebook upload and HRIS management are handled via the
      Admin Web Panel (admin_panel/). Run `python -m admin_panel.run`.
"""

from __future__ import annotations

import json
import re
from typing import Optional

import structlog
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.config import get_settings

log      = structlog.get_logger(__name__)
settings = get_settings()

# ─────────────────────────────────────────────────────────────────────────────
# MarkdownV2 escaping helper
# ─────────────────────────────────────────────────────────────────────────────

_MDV2_SPECIAL = re.compile(r"([_\*\[\]\(\)~`>#+\-=|{}.!\\])")

def _esc(text: str) -> str:
    """Escape all MarkdownV2 special characters."""
    return _MDV2_SPECIAL.sub(r"\\\1", str(text))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


# ─────────────────────────────────────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────────────────────────────────────

_START_TEXT = """
🤖 *MUGEN AI — Asset Request System*

Hello, *{name}*\\! I'm your enterprise asset\\-request agent\\.

Here's what I can do:
• 📦 Process asset requests with full policy validation
• 📜 Query your company rulebook via live RAG pipeline
• 🧩 Top\\-3 graded policy chunks inform every decision
• 🛡️ Every message passes through 6\\-signal security

*Commands*
`/request`   — Start a new asset request
`/status`    — Check your latest request
`/history`   — View your last 10 requests
`/cancel`    — Cancel current request
"""


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    name = _esc(user.first_name if user else "there")
    await update.message.reply_text(
        _START_TEXT.format(name=name),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    log.info("cmd_start", user_id=user.id if user else None)


# ─────────────────────────────────────────────────────────────────────────────
# /status — MARKDOWN_V2 confirmation card
# ─────────────────────────────────────────────────────────────────────────────

_STATUS_ICON = {
    "PENDING":      "⏳",
    "APPROVED":     "✅",
    "REJECTED":     "❌",
    "NEEDS_REVIEW": "🔍",
    "CANCELLED":    "🚫",
}
_RAG_BADGE = {
    "STRONG": "🟢 Strong",
    "WEAK":   "🟡 Weak",
    "NONE":   "⚪ None",
}


def _build_status_card(req: dict) -> str:
    """
    Render a rich MARKDOWN_V2 status card for a single request row.
    All dynamic values are escaped through _esc().
    """
    status  = req.get("status", "PENDING")
    icon    = _STATUS_ICON.get(status, "❓")

    rag_sig = _RAG_BADGE.get(req.get("rag_signal") or "NONE", "⚪ None")

    refs_raw = req.get("policy_refs") or "[]"
    try:
        refs_list = json.loads(refs_raw) if isinstance(refs_raw, str) else refs_raw
    except Exception:
        refs_list = []
    refs_str = (
        "\n".join(f"  • {_esc(r)}" for r in refs_list[:5])
        if refs_list else "  _none_"
    )

    cost = req.get("cost_estimate")
    cost_str = f"\\${_esc(f'{cost:,.0f}')}" if cost else "_unknown_"

    alt = req.get("suggested_alternative")
    alt_block = (
        f"\n💡 *Suggested Alternative*\n  {_esc(alt)}"
        if alt else ""
    )

    reason = _esc(req.get("decision_reason") or "Pending decision…")
    created = _esc(str(req.get("created_at", ""))[:16])

    return (
        f"┌─────────────────────────────────┐\n"
        f"│  {icon} *MUGEN AI — Request Card*       │\n"
        f"└─────────────────────────────────┘\n\n"
        f"📋 *Request ID*      `{_esc(req['id'])}`\n"
        f"📦 *Asset*           {_esc(req.get('asset_name') or '—')}\n"
        f"💰 *Est\\. Cost*      {cost_str}\n"
        f"⚡ *Urgency*         {_esc(req.get('urgency') or '—')}\n"
        f"🎓 *Employee Grade*  {_esc(req.get('employee_grade') or '—')}\n"
        f"🔍 *RAG Signal*      {rag_sig}\n"
        f"📅 *Submitted*       {created}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*Status:* {icon} `{_esc(status)}`\n\n"
        f"*Reasoning:*\n{reason}"
        + alt_block
        + f"\n\n*Policy References:*\n{refs_str}\n\n"
        f"_Track again anytime with_ `/status {_esc(req['id'])}`"
    )


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from bot.db.repository import get_latest_request, get_request_by_id

    user = update.effective_user
    args = context.args or []

    if args:
        req_id = args[0].upper()
        req = await get_request_by_id(req_id)
        if req is None:
            await update.message.reply_text(
                f"❌ No request found with ID `{_esc(req_id)}`\\.\n\n"
                "_Use_ `/history` _to see your recent requests\\._",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return
    else:
        req = await get_latest_request(user_id=user.id)
        if req is None:
            await update.message.reply_text(
                "❌ You have no requests yet\\. Start one with `/request`\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return

    if req["user_id"] != user.id and not _is_admin(user.id):
        await update.message.reply_text(
            "⛔ You can only view your own requests\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    card = _build_status_card(req)
    await update.message.reply_text(card, parse_mode=ParseMode.MARKDOWN_V2)
    log.info("cmd_status", user_id=user.id, req_id=req["id"])


# ─────────────────────────────────────────────────────────────────────────────
# /history — paginated request list
# ─────────────────────────────────────────────────────────────────────────────

_HIST_ICONS = {
    "PENDING":      "⏳",
    "APPROVED":     "✅",
    "REJECTED":     "❌",
    "NEEDS_REVIEW": "🔍",
    "CANCELLED":    "🚫",
}


async def handle_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from bot.db.repository import get_user_history

    user = update.effective_user
    rows = await get_user_history(user_id=user.id, limit=10)

    if not rows:
        await update.message.reply_text(
            "📋 No requests found\\. Start one with `/request`\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    lines = [f"📋 *Your last {len(rows)} request\\(s\\)*\n"]
    for r in rows:
        icon    = _HIST_ICONS.get(r.get("status", ""), "❓")
        cost    = r.get("cost_estimate")
        cost_s  = f"\\${_esc(f'{cost:,.0f}')}" if cost else "—"
        created = _esc(str(r.get("created_at", ""))[:10])
        alt     = r.get("suggested_alternative")
        alt_s   = f"\n     💡 _Alt: {_esc(alt)}_" if alt else ""
        lines.append(
            f"\n{icon} `{_esc(r['id'])}` — {_esc(r.get('asset_name') or '?')}\n"
            f"     Status: *{_esc(r.get('status','?'))}* · Cost: {cost_s} · {created}"
            + alt_s
        )

    lines.append(
        "\n\n_Use_ `/status <id>` _for a full decision card\\._"
    )
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    log.info("cmd_history", user_id=user.id, count=len(rows))


# ─────────────────────────────────────────────────────────────────────────────
# /cancel
# ─────────────────────────────────────────────────────────────────────────────

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from bot.db.repository import cancel_session

    user       = update.effective_user
    session_id = (context.user_data or {}).get("session_id")

    if session_id:
        await cancel_session(session_id=session_id)

    if context.user_data:
        context.user_data.clear()

    await update.message.reply_text(
        "🚫 Request cancelled\\. Start a new one anytime with `/request`\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    log.info("cmd_cancel", user_id=user.id, session_id=session_id)
