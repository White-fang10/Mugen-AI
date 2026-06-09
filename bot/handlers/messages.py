"""
bot/handlers/messages.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — Catch-all Message Handler
══════════════════════════════════════════════════════════════════════════════
Routes non-command text messages to the active SlotMachine for the user.
At this point the security middleware has already run (group -999) so we
know the message is safe.
"""

from __future__ import annotations

import structlog
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

log = structlog.get_logger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dispatch message to the active slot machine (if any)."""
    from bot.slots.state import SlotMachine

    user = update.effective_user
    text = update.message.text or ""

    machine: SlotMachine | None = (context.user_data or {}).get("slot_machine")

    if machine is None:
        # No active session — nudge user
        await update.message.reply_text(
            "💬 Type `/request` to start a new asset request, "
            "or `/help` to see available commands.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Hand off to slot machine
    response = await machine.process(text)
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

    log.info(
        "message_processed",
        user_id=user.id,
        session_id=(context.user_data or {}).get("session_id"),
    )
