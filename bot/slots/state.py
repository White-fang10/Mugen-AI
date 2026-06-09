"""
bot/slots/state.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — Slot Machine (Conversation State Manager)
══════════════════════════════════════════════════════════════════════════════
Implements a finite-state conversation that progressively fills all required
slots for an asset request, then passes the completed form to the decision
engine for LLM-powered policy validation.

States
──────
  COLLECTING  →  slots being gathered via NLP extractor
  CONFIRMING  →  summary shown, waiting for yes/no
  DECIDING    →  decision engine running
  DONE        →  terminal; result delivered
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

import structlog

from bot.slots.extractor import extract_slots

log = structlog.get_logger(__name__)


class ConversationState(str, Enum):
    COLLECTING = "COLLECTING"
    CONFIRMING = "CONFIRMING"
    DECIDING   = "DECIDING"
    DONE       = "DONE"


# Ordered list of slots and their friendly prompts
_SLOT_PROMPTS: list[tuple[str, str]] = [
    ("asset_name",      "🖥️ *What asset do you need?*\n_e.g. MacBook Pro 14\", Logitech MX Keys_"),
    ("justification",   "📝 *Why do you need this asset?*\n_Brief business justification_"),
    ("urgency",         "⏱️ *How urgent is this?*\n_Reply: HIGH / NORMAL / LOW_"),
    ("cost_estimate",   "💰 *Approximate cost? (USD)*\n_Enter a number, or type 'unknown'_"),
]

_REQUIRED_SLOTS = {k for k, _ in _SLOT_PROMPTS}


class SlotMachine:
    """Manages multi-turn conversation state for a single asset request."""

    def __init__(self, user_id: int) -> None:
        self.user_id  = user_id
        self.state    = ConversationState.COLLECTING
        self.slots: Dict[str, Any] = {}
        self._pending_slot_idx = 0  # which slot we're currently collecting

    # ── Public API ────────────────────────────────────────────────────────────

    async def process(self, text: str) -> str:
        """
        Main entry-point called by handle_message.
        Routes text to the correct handler based on current state.
        """
        if self.state == ConversationState.COLLECTING:
            return await self._collect(text)
        if self.state == ConversationState.CONFIRMING:
            return await self._confirm(text)
        if self.state == ConversationState.DECIDING:
            return "⏳ Decision in progress, please wait…"
        return "✅ Your request has already been submitted."

    @property
    def is_complete(self) -> bool:
        return _REQUIRED_SLOTS.issubset(self.slots)

    # ── Private state handlers ────────────────────────────────────────────────

    async def _collect(self, text: str) -> str:
        """Extract slot values from free-text using the NLP extractor."""
        # Try to extract any slots from the message
        extracted = await extract_slots(text, current_slot=self._current_slot_name())
        self.slots.update({k: v for k, v in extracted.items() if v is not None})

        # Advance to next missing slot
        missing = self._next_missing_slot()
        if missing:
            slot_name, prompt = missing
            return prompt
        else:
            # All slots filled — move to confirmation
            self.state = ConversationState.CONFIRMING
            return self._build_summary()

    async def _confirm(self, text: str) -> str:
        """Handle yes/no confirmation."""
        lower = text.lower().strip()
        affirmative = any(w in lower for w in ["yes", "confirm", "ok", "proceed", "y", "sure"])
        negative    = any(w in lower for w in ["no", "cancel", "abort", "n", "stop"])

        if affirmative:
            self.state = ConversationState.DECIDING
            return await self._run_decision()

        if negative:
            self.state = ConversationState.COLLECTING
            self.slots.clear()
            self._pending_slot_idx = 0
            return (
                "🔄 Request reset. Let's start over.\n\n"
                + _SLOT_PROMPTS[0][1]
            )

        return (
            "❓ Please reply with *Yes* to confirm or *No* to restart.\n\n"
            + self._build_summary()
        )

    async def _run_decision(self) -> str:
        """Call the decision engine and format the result."""
        try:
            from bot.validation.decision import evaluate_request
            from bot.db.repository import create_request, update_request_decision, append_audit

            # Persist the request
            session_id = 0  # placeholder; real session_id injected via user_data
            req_id = await create_request(
                session_id=session_id,
                user_id=self.user_id,
                slots=self.slots,
            )

            # Run policy evaluation
            verdict = await evaluate_request(self.slots)
            await update_request_decision(
                request_id=req_id,
                status=verdict.status,
                reason=verdict.reason,
                policy_refs=verdict.policy_refs,
            )
            await append_audit(req_id, actor="MUGEN_AI", action=verdict.status, detail=verdict.reason)

            self.state = ConversationState.DONE

            emoji = "✅" if verdict.status == "APPROVED" else (
                "🔍" if verdict.status == "NEEDS_REVIEW" else "❌"
            )
            refs = "\n".join(f"  • _{r}_" for r in verdict.policy_refs) if verdict.policy_refs else "  _None cited_"

            return (
                f"{emoji} *Decision: {verdict.status}*\n\n"
                f"*Request ID:* `{req_id}`\n\n"
                f"*Reasoning:*\n{verdict.reason}\n\n"
                f"*Policy References:*\n{refs}\n\n"
                f"_Use `/status {req_id}` to track this request._"
            )

        except Exception as exc:
            log.error("decision_failed", error=str(exc), user_id=self.user_id)
            self.state = ConversationState.DONE
            return "❌ An error occurred during evaluation. Please try again later."

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _current_slot_name(self) -> Optional[str]:
        if self._pending_slot_idx < len(_SLOT_PROMPTS):
            return _SLOT_PROMPTS[self._pending_slot_idx][0]
        return None

    def _next_missing_slot(self) -> Optional[tuple[str, str]]:
        for slot_name, prompt in _SLOT_PROMPTS:
            if slot_name not in self.slots:
                return slot_name, prompt
        return None

    def _build_summary(self) -> str:
        cost = self.slots.get("cost_estimate", "Unknown")
        cost_str = f"${cost:,.0f}" if isinstance(cost, (int, float)) else str(cost)
        return (
            "📋 *Request Summary*\n\n"
            f"Asset: `{self.slots.get('asset_name', '—')}`\n"
            f"Justification: _{self.slots.get('justification', '—')}_\n"
            f"Urgency: `{self.slots.get('urgency', '—')}`\n"
            f"Est. Cost: `{cost_str}`\n\n"
            "Type *Yes* to submit or *No* to restart."
        )
