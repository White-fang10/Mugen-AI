"""
bot/handlers/conversation.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — Stage 2: PTB ConversationHandler
══════════════════════════════════════════════════════════════════════════════

Implements a python-telegram-bot v20 ConversationHandler for the full
/request → slot collection → confirm → decision flow.

States
──────
  SLOT_COLLECT   — bot is filling slots one-by-one via SlotMachine
  CONFIRMING     — summary shown, waiting for yes/no
  (FROZEN/DONE are terminal; ConversationHandler.END is returned)

Why use ConversationHandler here?
──────────────────────────────────
  The SlotMachine already tracks state internally, but PTB's
  ConversationHandler provides:
    • Clean conversation lifecycle (timeout, per-user state isolation)
    • Fallback on unexpected messages (/cancel, errors)
    • Automatic END when the session terminates (frozen or done)

Security guarantee
──────────────────
  security_middleware (group -999) still runs on EVERY message —
  the ConversationHandler does not bypass it.
  An additional check inside each handler verifies the session hasn't
  been frozen by the NLP layer (double-gate pattern).
"""

from __future__ import annotations

import structlog
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.slots.state import ConversationState, SlotMachine

log = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# ConversationHandler state keys (integers, as PTB requires)
# ─────────────────────────────────────────────────────────────────────────────

SLOT_COLLECT = 0
CONFIRMING   = 1

# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _get_machine(context: ContextTypes.DEFAULT_TYPE) -> SlotMachine | None:
    return (context.user_data or {}).get("slot_machine")


def _set_machine(context: ContextTypes.DEFAULT_TYPE, machine: SlotMachine) -> None:
    if context.user_data is not None:
        context.user_data["slot_machine"] = machine


# ─────────────────────────────────────────────────────────────────────────────
# Entry point — /request
# ─────────────────────────────────────────────────────────────────────────────

async def conv_start_request(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Entry point for the /request ConversationHandler.
    Creates a fresh SlotMachine and sends the first slot prompt.
    """
    from bot.db.repository import upsert_session

    user = update.effective_user
    user_id = user.id

    # Create a DB session
    session_id = await upsert_session(user_id=user_id, state=ConversationState.COLLECTING)
    machine = SlotMachine(user_id=user_id, session_id=session_id)
    _set_machine(context, machine)

    if context.user_data is not None:
        context.user_data["session_id"] = session_id

    opening = machine.get_opening_prompt()
    await update.message.reply_text(
        f"📋 *New Asset Request* — Let's get started!\n\n{opening}",
        parse_mode=ParseMode.MARKDOWN,
    )
    log.info("conv_request_started", user_id=user_id, session_id=session_id)
    return SLOT_COLLECT


# ─────────────────────────────────────────────────────────────────────────────
# SLOT_COLLECT state handler
# ─────────────────────────────────────────────────────────────────────────────

async def conv_collect_slot(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Receives user text, feeds it to the SlotMachine, sends back the response.
    Transitions:
      • Still collecting → stay in SLOT_COLLECT
      • Machine is now in CONFIRMING → move to CONFIRMING state
      • Machine is FROZEN or DONE → END conversation
    """
    machine = _get_machine(context)
    if machine is None:
        await update.message.reply_text(
            "❓ Session lost. Please use /request to start over.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    # Double-gate: check if security middleware already froze this machine
    if machine.frozen:
        await update.message.reply_text(
            "🔒 This session is frozen. Use /request to start a new one.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END

    text = update.message.text or ""
    response = await machine.process(text)

    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

    if machine.frozen or machine.done:
        log.info(
            "conv_terminated",
            user_id=update.effective_user.id,
            reason="frozen" if machine.frozen else "done",
        )
        return ConversationHandler.END

    # Check if machine transitioned to CONFIRMING
    if machine.state == ConversationState.CONFIRMING:
        return CONFIRMING

    return SLOT_COLLECT


# ─────────────────────────────────────────────────────────────────────────────
# CONFIRMING state handler
# ─────────────────────────────────────────────────────────────────────────────

async def conv_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handles yes/no confirmation. Delegates fully to SlotMachine._confirm().
    On yes → DECIDING → DONE → END.
    On no  → back to SLOT_COLLECT.
    """
    machine = _get_machine(context)
    if machine is None:
        return ConversationHandler.END

    text = update.message.text or ""
    response = await machine.process(text)

    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

    if machine.frozen or machine.done:
        return ConversationHandler.END

    # "No" resets machine back to COLLECTING
    if machine.state == ConversationState.COLLECTING:
        return SLOT_COLLECT

    return CONFIRMING


# ─────────────────────────────────────────────────────────────────────────────
# Cancel fallback (available in any state)
# ─────────────────────────────────────────────────────────────────────────────

async def conv_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Global /cancel fallback — reachable from any conversation state."""
    from bot.db.repository import cancel_session

    user = update.effective_user
    session_id = (context.user_data or {}).get("session_id")

    if session_id:
        await cancel_session(session_id=session_id)

    if context.user_data:
        context.user_data.pop("slot_machine", None)
        context.user_data.pop("session_id", None)

    await update.message.reply_text(
        "🚫 *Request cancelled.*\n\nUse /request whenever you're ready to try again.",
        parse_mode=ParseMode.MARKDOWN,
    )
    log.info("conv_cancelled", user_id=user.id, session_id=session_id)
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
# Timeout fallback
# ─────────────────────────────────────────────────────────────────────────────

async def conv_timeout(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Called when the conversation times out (no message for 10 minutes)."""
    if update.effective_message:
        await update.effective_message.reply_text(
            "⏰ *Session timed out* (10 minutes of inactivity).\n\n"
            "Use /request to start a new asset request.",
            parse_mode=ParseMode.MARKDOWN,
        )
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
# ConversationHandler factory
# ─────────────────────────────────────────────────────────────────────────────

def build_request_conversation() -> ConversationHandler:
    """
    Build and return the fully configured PTB ConversationHandler.
    Register this with app.add_handler() in main.py.
    """
    return ConversationHandler(
        entry_points=[
            CommandHandler("request", conv_start_request),
        ],
        states={
            SLOT_COLLECT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    conv_collect_slot,
                ),
            ],
            CONFIRMING: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    conv_confirm,
                ),
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, conv_timeout),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", conv_cancel),
            # Any other command in mid-conversation → soft cancel
            MessageHandler(filters.COMMAND, conv_cancel),
        ],
        conversation_timeout=600,           # 10 minutes
        allow_reentry=True,                 # /request mid-conversation restarts
        name="asset_request_conversation",
        persistent=False,
    )
