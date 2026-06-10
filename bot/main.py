"""
bot/main.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — SD-05 Telegram Asset Request Bot
══════════════════════════════════════════════════════════════════════════════
Simple slot-filling bot that:
  1. Collects asset request via conversation (slot-filling)
  2. Validates against predefined HRIS data (role, grade, budget)
  3. Saves structured request JSON to SQLite
  4. Returns APPROVED / FLAGGED / REJECTED decision
"""

from __future__ import annotations

import logging
import sys

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
    handle_cancel,
    handle_history,
    handle_start,
    handle_status,
)
from bot.handlers.conversation import build_request_conversation


# ─────────────────────────────────────────────────────────────────────────────
# Logging bootstrap
# ─────────────────────────────────────────────────────────────────────────────

def _configure_logging(level: str = "INFO") -> None:
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
# Application factory
# ─────────────────────────────────────────────────────────────────────────────

def build_application() -> Application:
    app = (
        Application.builder()
        .token(settings.bot_token)
        .arbitrary_callback_data(True)
        .build()
    )

    # ConversationHandler for /request flow (must be registered first)
    app.add_handler(build_request_conversation())

    # Standalone command handlers
    app.add_handler(CommandHandler("start",   handle_start))
    app.add_handler(CommandHandler("status",  handle_status))
    app.add_handler(CommandHandler("history", handle_history))
    app.add_handler(CommandHandler("cancel",  handle_cancel))

    # Catch-all: messages outside any active conversation
    async def _orphan_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message:
            await update.message.reply_text(
                "💬 Use /request to start an asset request, or /start to see all commands."
            )

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _orphan_message))
    return app


# ─────────────────────────────────────────────────────────────────────────────
# Boot
# ─────────────────────────────────────────────────────────────────────────────

async def _on_startup(app: Application) -> None:
    log.info("mugen_ai_starting")
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    await init_db()
    log.info("database_ready", path=str(settings.db_path))


def main() -> None:
    _configure_logging(settings.log_level)
    log.info("booting_mugen_ai", version="3.0.0-simple")

    app = build_application()
    app.post_init = _on_startup  # type: ignore[assignment]

    log.info("starting_polling")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
