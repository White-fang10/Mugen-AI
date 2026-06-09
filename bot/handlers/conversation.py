"""
bot/handlers/conversation.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — Stage 6: Production ConversationHandler
══════════════════════════════════════════════════════════════════════════════

PTB states
──────────
  SLOT_COLLECT   Filling slots one-by-one via SlotMachine
  CONFIRMING     Summary shown, waiting for yes / no

Edge cases handled (Stage 6)
─────────────────────────────
  • Mid-conversation /cancel        → graceful DB cancel + friendly message
  • 10-minute timeout               → auto-cancel with friendly timeout notice
  • Sticker sent during collection  → polite "text only" nudge, stay in state
  • Photo / video / document sent   → same nudge pattern
  • Unknown / empty message         → safe fallback, no crash
  • Session lost (user_data reset)  → "session lost" message + END
  • FROZEN session double-gate      → block with freeze message + END
  • Any other command mid-flow      → treated as /cancel (PTB fallback rule)

Security guarantees
────────────────────
  • security_middleware (group -999) runs on EVERY update before this handler.
  • SuspicionScorer instance is stored per-session in user_data and
    accumulates points across the conversation.
  • inject_risk=high from the NLP layer → machine.frozen → END.
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
# PTB conversation state keys
# ─────────────────────────────────────────────────────────────────────────────

SLOT_COLLECT = 0
CONFIRMING   = 1

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_machine(context: ContextTypes.DEFAULT_TYPE) -> SlotMachine | None:
    return (context.user_data or {}).get("slot_machine")


def _set_machine(context: ContextTypes.DEFAULT_TYPE, machine: SlotMachine) -> None:
    if context.user_data is not None:
        context.user_data["slot_machine"] = machine


async def _safe_reply(update: Update, text: str) -> None:
    """Reply helper that silently swallows errors (e.g. message deleted)."""
    try:
        if update.effective_message:
            await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        pass


async def _do_cancel(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """Shared cancel teardown: cancel DB session + clear user_data."""
    from bot.db.repository import cancel_session
    session_id = (context.user_data or {}).get("session_id")
    if session_id:
        try:
            await cancel_session(session_id=session_id)
        except Exception:
            pass
    if context.user_data:
        context.user_data.pop("slot_machine", None)
        context.user_data.pop("session_id", None)
    log.info("session_cancelled", user_id=user_id, session_id=session_id)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point — /request
# ─────────────────────────────────────────────────────────────────────────────

async def conv_start_request(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    /request entry point.
    Creates a fresh SlotMachine and sends the first slot prompt.
    If allow_reentry=True fires while a session is already open, it
    cleanly cancels the old session first.
    """
    from bot.db.repository import upsert_session

    user    = update.effective_user
    user_id = user.id

    # Clean up any abandoned session
    old_session = (context.user_data or {}).get("session_id")
    if old_session:
        await _do_cancel(context, user_id)

    session_id = await upsert_session(user_id=user_id, state=ConversationState.COLLECTING)
    machine    = SlotMachine(user_id=user_id, session_id=session_id)
    _set_machine(context, machine)

    if context.user_data is not None:
        context.user_data["session_id"] = session_id

    opening = machine.get_opening_prompt()
    await _safe_reply(
        update,
        f"📋 *New Asset Request* — Let's get started\\!\n\n{opening}",
    )
    log.info("conv_request_started", user_id=user_id, session_id=session_id)
    return SLOT_COLLECT


# ─────────────────────────────────────────────────────────────────────────────
# Media interruption handler (stickers, photos, video, voice, etc.)
# ─────────────────────────────────────────────────────────────────────────────

async def conv_media_interrupt(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Gracefully handle non-text messages (stickers, images, audio, etc.)
    sent during slot collection. Nudges the user back to text input
    without advancing or resetting the slot state.
    """
    msg = update.effective_message

    # Detect what was sent
    if msg.sticker:
        label = "a sticker"
        extra = " 😄"
    elif msg.photo:
        label = "a photo"
        extra = ""
    elif msg.video:
        label = "a video"
        extra = ""
    elif msg.voice or msg.audio:
        label = "a voice/audio message"
        extra = ""
    elif msg.document:
        label = "a document"
        extra = " _(use /upload_rulebook for PDFs)_"
    else:
        label = "that"
        extra = ""

    machine = _get_machine(context)
    current_slot = machine.active_slot if machine else None
    slot_hint = f"\n\n*Current question:* _{machine.get_current_prompt()}_" if machine and current_slot else ""

    await _safe_reply(
        update,
        f"📝 I received {label}{extra}, but I need a *text reply* to continue your request.{slot_hint}",
    )

    # Return to the same state we were in
    if machine and machine.state == ConversationState.CONFIRMING:
        return CONFIRMING
    return SLOT_COLLECT


# ─────────────────────────────────────────────────────────────────────────────
# SLOT_COLLECT state handler
# ─────────────────────────────────────────────────────────────────────────────

async def conv_collect_slot(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Receives user text → feeds to SlotMachine → sends response.
    Handles:
      • Empty / whitespace input → re-prompt gently
      • machine is None (session lost) → END
      • machine.frozen (injection detected) → END
      • machine.done → END
      • machine transitions to CONFIRMING → CONFIRMING state
    """
    machine = _get_machine(context)

    if machine is None:
        await _safe_reply(
            update,
            "❓ Your session was lost\\. Use /request to start over\\.",
        )
        return ConversationHandler.END

    # Double-gate: NLP layer may have already frozen the machine
    if machine.frozen:
        await _safe_reply(
            update,
            "🔒 This session is permanently frozen\\. Use /request to start a new one\\.",
        )
        return ConversationHandler.END

    text = (update.message.text or "").strip()
    if not text:
        await _safe_reply(update, "💬 Please type a response to continue\\.")
        return SLOT_COLLECT

    response = await machine.process(text)
    await _safe_reply(update, response)

    if machine.frozen:
        log.info("conv_frozen", user_id=update.effective_user.id)
        return ConversationHandler.END

    if machine.done:
        log.info("conv_done", user_id=update.effective_user.id)
        return ConversationHandler.END

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
    Handles yes / no confirmation reply.
      yes → decision engine → DONE → END
      no  → reset to COLLECTING → SLOT_COLLECT
    """
    machine = _get_machine(context)
    if machine is None:
        return ConversationHandler.END

    text = (update.message.text or "").strip()
    if not text:
        await _safe_reply(
            update,
            "💬 Please reply *yes* to submit or *no* to restart\\.",
        )
        return CONFIRMING

    response = await machine.process(text)
    await _safe_reply(update, response)

    if machine.frozen or machine.done:
        return ConversationHandler.END

    if machine.state == ConversationState.COLLECTING:
        return SLOT_COLLECT

    return CONFIRMING


# ─────────────────────────────────────────────────────────────────────────────
# /cancel fallback — reachable from any state
# ─────────────────────────────────────────────────────────────────────────────

async def conv_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Mid-conversation /cancel (also catches any other command used mid-flow).
    Gracefully cancels DB session and clears user_data.
    """
    user = update.effective_user
    await _do_cancel(context, user.id)

    await _safe_reply(
        update,
        "🚫 *Request cancelled\\.* \\— No worries\\!\n\nUse /request whenever you're ready to try again\\.",
    )
    log.info("conv_cancelled", user_id=user.id)
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
# Timeout handler
# ─────────────────────────────────────────────────────────────────────────────

async def conv_timeout(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Called by PTB when the conversation has been idle for 10 minutes.
    Auto-cancels the DB session so it doesn't stay open forever.
    """
    user_id = update.effective_user.id if update.effective_user else 0
    await _do_cancel(context, user_id)

    await _safe_reply(
        update,
        "⏰ *Session timed out* \\(10 minutes of inactivity\\)\\.\n\n"
        "Your in\\-progress request was discarded\\. Use /request to start a new one\\.",
    )
    log.info("conv_timeout", user_id=user_id)
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
# ConversationHandler factory
# ─────────────────────────────────────────────────────────────────────────────

def build_request_conversation() -> ConversationHandler:
    """
    Build the fully configured PTB ConversationHandler.
    Registered in main.py BEFORE standalone command handlers.
    """
    _media_filter = (
        filters.PHOTO
        | filters.VIDEO
        | filters.Sticker.ALL
        | filters.VOICE
        | filters.AUDIO
        | filters.Document.ALL
        | filters.ANIMATION
    )

    return ConversationHandler(
        entry_points=[
            CommandHandler("request", conv_start_request),
        ],
        states={
            SLOT_COLLECT: [
                # Text input → slot collection
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    conv_collect_slot,
                ),
                # Media interruption → gentle nudge, stay in state
                MessageHandler(_media_filter, conv_media_interrupt),
            ],
            CONFIRMING: [
                # Text confirmation → yes / no
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    conv_confirm,
                ),
                # Media in confirmation state → same nudge
                MessageHandler(_media_filter, conv_media_interrupt),
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, conv_timeout),
            ],
        },
        fallbacks=[
            # /cancel from any state
            CommandHandler("cancel", conv_cancel),
            # Any other command mid-conversation → treated as cancel
            MessageHandler(filters.COMMAND, conv_cancel),
        ],
        conversation_timeout=600,       # 10 minutes
        allow_reentry=True,             # /request mid-conv restarts cleanly
        name="asset_request_conversation",
        persistent=False,
    )
