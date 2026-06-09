"""
bot/handlers/commands.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — Command Handlers
══════════════════════════════════════════════════════════════════════════════
Implements:
  /start           — Welcome & capability overview
  /request         — Kick off a new asset request conversation
  /status          — Look up status of an existing request
  /cancel          — Abort an in-progress conversation
  /upload_rulebook — Admin-only: accept a PDF and ingest into RAG store
  document handler — Handle PDF document messages (post /upload_rulebook)
"""

from __future__ import annotations

import structlog
from telegram import Document, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


def _get_suspicion(context: ContextTypes.DEFAULT_TYPE) -> float:
    """Retrieve the suspicion score placed by security middleware."""
    from bot.main import SECURITY_KEY
    result = (context.user_data or {}).get(SECURITY_KEY)
    return result.score if result else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────────────────────────────────────

_START_TEXT = """
🤖 *MUGEN AI — Asset Request System*

Hello, *{name}*! I'm your enterprise asset-request agent.

Here's what I can do:
• 📦 Process asset requests with full policy validation
• 📜 Query your company rulebook via live RAG pipeline
• 🔍 Track request status in real-time
• 🧩 Top-3 graded policy chunks inform every decision
• 🛡️ Every message passes through 6-signal security

*Commands*
`/request`           — Start a new asset request
`/status <id>`       — Check an existing request
`/cancel`            — Cancel current request
`/upload_rulebook`   — _(Admin)_ Index a policy PDF

_Powered by LLaMA 3.3 · 70B · Groq + ChromaDB RAG_
"""


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    name = user.first_name if user else "there"
    await update.message.reply_text(
        _START_TEXT.format(name=name),
        parse_mode=ParseMode.MARKDOWN,
    )
    log.info("cmd_start", user_id=user.id if user else None)


# NOTE: /request is now handled by the ConversationHandler in
# bot/handlers/conversation.py → conv_start_request()

# ─────────────────────────────────────────────────────────────────────────────
# /status
# ─────────────────────────────────────────────────────────────────────────────

async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from bot.db.repository import get_request_by_id, get_latest_request

    user = update.effective_user
    args = context.args or []

    if args:
        req = await get_request_by_id(request_id=args[0])
    else:
        req = await get_latest_request(user_id=user.id)

    if req is None:
        await update.message.reply_text(
            "❌ No request found. Start one with `/request`.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    status_emoji = {
        "PENDING": "⏳",
        "APPROVED": "✅",
        "REJECTED": "❌",
        "NEEDS_REVIEW": "🔍",
        "CANCELLED": "🚫",
    }.get(req["status"], "❓")

    await update.message.reply_text(
        f"*Request #{req['id']}*\n\n"
        f"Asset: `{req['asset_name']}`\n"
        f"Status: {status_emoji} *{req['status']}*\n"
        f"Submitted: {req['created_at']}\n\n"
        f"_{req.get('decision_reason', 'Processing...')}_",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─────────────────────────────────────────────────────────────────────────────
# /cancel
# ─────────────────────────────────────────────────────────────────────────────

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from bot.db.repository import cancel_session

    user = update.effective_user
    session_id = (context.user_data or {}).get("session_id")

    if session_id:
        await cancel_session(session_id=session_id)

    context.user_data.clear()

    await update.message.reply_text(
        "🚫 Request cancelled. Start a new one anytime with `/request`.",
        parse_mode=ParseMode.MARKDOWN,
    )
    log.info("cmd_cancel", user_id=user.id, session_id=session_id)


# ─────────────────────────────────────────────────────────────────────────────
# /upload_rulebook  (admin-only)
# ─────────────────────────────────────────────────────────────────────────────

async def handle_upload_rulebook(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    from bot.rag.retriever import get_indexed_sources, has_rulebook

    user = update.effective_user

    if not _is_admin(user.id):
        await update.message.reply_text(
            "⛔ This command is restricted to administrators.",
            parse_mode=ParseMode.MARKDOWN,
        )
        log.warning("unauthorised_rulebook_upload", user_id=user.id)
        return

    context.user_data["awaiting_rulebook"] = True

    # Show currently indexed sources
    if has_rulebook():
        sources = get_indexed_sources()
        source_list = "\n".join(f"  • `{s}`" for s in sources) or "  _None yet_"
        indexed_block = f"\n\n*Currently indexed rulebooks:*\n{source_list}"
    else:
        indexed_block = "\n\n_No rulebooks indexed yet — this will be the first._"

    await update.message.reply_text(
        "📚 *Admin — Rulebook Upload*\n\n"
        "Send a policy PDF to index it into the RAG store.\n"
        "_Supported: PDF up to 50 MB · Duplicates are detected automatically_"
        + indexed_block,
        parse_mode=ParseMode.MARKDOWN,
    )
    log.info("awaiting_rulebook_pdf", admin_id=user.id)


# ─────────────────────────────────────────────────────────────────────────────
# Document handler — handles PDF uploads after /upload_rulebook
# ─────────────────────────────────────────────────────────────────────────────

async def handle_document(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    from bot.rag.pdf_loader import IngestionReport, ingest_pdf

    user = update.effective_user
    awaiting = (context.user_data or {}).get("awaiting_rulebook", False)

    if not awaiting:
        await update.message.reply_text(
            "📎 To upload a rulebook, use `/upload_rulebook` first.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not _is_admin(user.id):
        await update.message.reply_text("⛔ Admin access required.")
        return

    doc: Document = update.message.document
    if not doc.file_name.lower().endswith(".pdf"):
        await update.message.reply_text(
            "❌ Only PDF files are accepted. Please send a `.pdf` document."
        )
        return

    # Acknowledge immediately — ingestion can take several seconds
    status_msg = await update.message.reply_text(
        "⏳ *Downloading PDF…*",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        # ── Download from Telegram ────────────────────────────────────────────
        tg_file = await context.bot.get_file(doc.file_id)
        dest = settings.rulebooks_dir / doc.file_name
        await tg_file.download_to_drive(str(dest))

        await status_msg.edit_text(
            "⏳ *PDF downloaded. Extracting text and building vectors…*\n"
            "_This may take 10–60 seconds depending on file size._",
            parse_mode=ParseMode.MARKDOWN,
        )

        # ── Ingest into ChromaDB (Stage 3 pipeline) ───────────────────────────
        report: IngestionReport = await ingest_pdf(
            pdf_path=dest,
            admin_id=user.id,
        )

        context.user_data["awaiting_rulebook"] = False

        # Pretty-print the IngestionReport
        reply = (
            f"📚 *Rulebook Ingestion Report*\n\n"
            + str(report)
        )
        await status_msg.edit_text(reply, parse_mode=ParseMode.MARKDOWN)
        log.info(
            "rulebook_ingested",
            file=doc.file_name,
            chunks=report.chunks_created,
            duplicate=report.was_duplicate,
            admin=user.id,
        )

    except ValueError as exc:
        # Validation errors (bad file, too large, no text, etc.)
        await status_msg.edit_text(
            f"❌ *Ingestion failed — validation error*\n\n`{exc}`",
            parse_mode=ParseMode.MARKDOWN,
        )
        log.warning("rulebook_validation_failed", error=str(exc))

    except Exception as exc:
        log.error("rulebook_ingest_failed", error=str(exc))
        await status_msg.edit_text(
            "❌ *Ingestion failed — internal error.*\n"
            "Please check server logs for details.",
            parse_mode=ParseMode.MARKDOWN,
        )
