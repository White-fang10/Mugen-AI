"""
bot/main.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — Application Entry-Point & Routing
══════════════════════════════════════════════════════════════════════════════
Boot sequence
  1. Initialise structured logging
  2. Ensure DB schema exists
  3. Build PTB Application
  4. Register the suspicion-guard middleware (fires before every handler)
  5. Register command handlers: /start, /request, /upload_rulebook
  6. Register the catch-all message guard
  7. Run polling (development) or webhook (production via env flag)
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import structlog
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.config import get_settings
from bot.db.schema import init_db
from bot.handlers.commands import (
    handle_request,
    handle_start,
    handle_upload_rulebook,
    handle_status,
    handle_cancel,
)
from bot.handlers.messages import handle_message
from bot.security.scorer import SuspicionResult, score_message

# ─────────────────────────────────────────────────────────────────────────────
# Logging bootstrap
# ─────────────────────────────────────────────────────────────────────────────

def _configure_logging(level: str = "INFO") -> None:
    """Wire structlog → stdlib so PTB's own loggers are captured too."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


log = structlog.get_logger(__name__)
settings = get_settings()

# ─────────────────────────────────────────────────────────────────────────────
# Security middleware — runs before EVERY handler
# ─────────────────────────────────────────────────────────────────────────────

QUARANTINE_MSG = (
    "⛔ *Security Alert*\n\n"
    "Your message has been flagged by MUGEN AI's security layer.\n"
    "If you believe this is a mistake, contact your system administrator.\n\n"
    "_Ref: {score}_"
)

SECURITY_KEY = "suspicion_result"


async def security_middleware(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Global pre-handler security gate.

    Extracts text from any update type that carries a user message,
    runs it through the suspicion scorer, and:

      • Stores the SuspicionResult on context.user_data so downstream
        handlers can inspect it.
      • If is_suspicious → sends a quarantine reply and raises
        ApplicationHandlerStop to abort the handler chain.

    Admin commands (/upload_rulebook) are not exempt — admins can still
    be compromised accounts.
    """
    from telegram.ext import ApplicationHandlerStop

    # Extract the text payload regardless of update type
    text = ""
    if update.message and update.message.text:
        text = update.message.text
    elif update.message and update.message.caption:
        text = update.message.caption
    elif update.edited_message and update.edited_message.text:
        text = update.edited_message.text
    elif update.callback_query and update.callback_query.data:
        text = update.callback_query.data

    # Resolve user_id
    user = (
        update.effective_user
        or (update.message and update.message.from_user)
        or (update.callback_query and update.callback_query.from_user)
    )
    if user is None:
        return  # Non-user update (channel posts etc.) — pass through

    user_id = user.id

    # Score it
    result: SuspicionResult = await score_message(user_id=user_id, text=text)

    # Persist on context for downstream handlers
    if context.user_data is not None:
        context.user_data[SECURITY_KEY] = result

    if result.is_suspicious:
        log.warning(
            "message_quarantined",
            user_id=user_id,
            score=result.score,
            signals=result.signals,
        )
        # Notify the user
        if update.effective_message:
            await update.effective_message.reply_text(
                QUARANTINE_MSG.format(score=result.score),
                parse_mode="Markdown",
            )
        # Log to DB (fire-and-forget)
        asyncio.create_task(_log_quarantine(result))
        # Halt the handler chain
        raise ApplicationHandlerStop


async def _log_quarantine(result: SuspicionResult) -> None:
    """Persist quarantine event to DB asynchronously."""
    try:
        from bot.db.repository import log_security_event
        await log_security_event(
            user_id=result.user_id,
            event_type="QUARANTINE",
            score=result.score,
            signals=result.signals,
            snippet=result.text_snippet,
        )
    except Exception as exc:
        log.error("quarantine_log_failed", error=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# Application factory
# ─────────────────────────────────────────────────────────────────────────────

def build_application() -> Application:
    """Construct and configure the PTB Application."""
    app = (
        Application.builder()
        .token(settings.bot_token)
        .arbitrary_callback_data(True)
        .build()
    )

    # ── Register security middleware (group -999 → runs first) ────────────────
    # PTB handler groups: lower number = higher priority.
    # Group -999 ensures the security gate runs before all business handlers.
    app.add_handler(
        MessageHandler(filters.ALL, security_middleware),
        group=-999,
    )

    # ── Command handlers ──────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",           handle_start))
    app.add_handler(CommandHandler("request",         handle_request))
    app.add_handler(CommandHandler("status",          handle_status))
    app.add_handler(CommandHandler("cancel",          handle_cancel))
    app.add_handler(CommandHandler("upload_rulebook", handle_upload_rulebook))

    # ── Catch-all message handler (slot filling / conversation flow) ──────────
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # ── Document handler (for rulebook PDF uploads) ───────────────────────────
    from bot.handlers.commands import handle_document
    app.add_handler(MessageHandler(filters.Document.PDF, handle_document))

    return app


# ─────────────────────────────────────────────────────────────────────────────
# Boot
# ─────────────────────────────────────────────────────────────────────────────

async def _on_startup(app: Application) -> None:
    """Async tasks that run once after the Application is initialised."""
    log.info("mugen_ai_starting")

    # Ensure directories exist
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    settings.rulebooks_dir.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)

    # Boot the database
    await init_db()
    log.info("database_ready", path=str(settings.db_path))


def main() -> None:
    _configure_logging(settings.log_level)
    log.info("booting_mugen_ai", version="1.0.0")

    app = build_application()

    # Register startup hook
    app.post_init = _on_startup  # type: ignore[assignment]

    log.info("starting_polling")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
