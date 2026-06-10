"""
bot/slots/state.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — Stage 2: Upgraded Slot Machine with Confidence Gating
══════════════════════════════════════════════════════════════════════════════

New in Stage 2
──────────────
  • Uses extract_slot() (returns ExtractionResult) instead of bare dicts.
  • Confidence thresholding:
      ≥ 0.70  → accepted, move to next slot
      0.40–0.69 → low confidence → bot re-asks with a gentle hint
      < 0.40  → failed → bot re-asks with the original prompt
  • injection_risk == "high" → session is FROZEN immediately:
      - State transitions to FROZEN (terminal)
      - Security event logged to DB
      - User notified with a firm, informative message
      - The slot machine will refuse further input
  • Tracks retry counts per slot to prevent infinite loops (max 3 retries).
  • Exposes `frozen` property so the ConversationHandler can end the conv.

State machine
─────────────
  COLLECTING  ──extract_slot()──▶ COLLECTING (next slot)
      │                              │
      │ (all slots filled)           │ (injection_risk=high)
      ▼                              ▼
  CONFIRMING ──yes──▶ DECIDING    FROZEN (terminal)
      │                 │
      │ no              ▼
      └──────────▶  COLLECTING  DONE (terminal)
"""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Any, Dict, Optional

import structlog

from bot.slots.extractor import CONFIDENCE_THRESHOLD, ExtractionResult, extract_slot

log = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

MAX_RETRIES_PER_SLOT = 3   # after this, slot is skipped with a default

# ─────────────────────────────────────────────────────────────────────────────
# State enum
# ─────────────────────────────────────────────────────────────────────────────

class ConversationState(str, Enum):
    COLLECTING = "COLLECTING"
    CONFIRMING = "CONFIRMING"
    DECIDING   = "DECIDING"
    FROZEN     = "FROZEN"      # 🆕 injection freeze terminal state
    DONE       = "DONE"


# ─────────────────────────────────────────────────────────────────────────────
# Slot definitions
# ─────────────────────────────────────────────────────────────────────────────

_SLOT_PROMPTS: list[tuple[str, str]] = [
    (
        "asset_name",
        "🖥️ *What asset do you need?*\n"
        "_e.g. MacBook Pro 14\", Dell Latitude 5540, Logitech MX Keys_",
    ),
    (
        "justification",
        "📝 *Why do you need this asset?*\n"
        "_Brief business justification — e.g. 'Replace broken laptop for video editing'_",
    ),
    (
        "urgency",
        "⏱️ *How urgent is this request?*\n"
        "_Reply with_ `HIGH` _(ASAP)_ · `NORMAL` _(standard)_ · `LOW` _(whenever)_",
    ),
    (
        "cost_estimate",
        "💰 *Approximate cost in USD?*\n"
        "_Enter a number like_ `1500` _or_ `2k`_, or type_ `unknown`",
    ),
]

_SLOT_NAMES = [s for s, _ in _SLOT_PROMPTS]
_SLOT_PROMPT_MAP = dict(_SLOT_PROMPTS)
_REQUIRED_SLOTS = set(_SLOT_NAMES)

# Low-confidence re-ask templates (appended after the original prompt)
_LOW_CONF_HINT: Dict[str, str] = {
    "asset_name":    "🤔 I didn't quite catch the product name. Could you be more specific?\n_e.g. 'MacBook Pro 14\" M3' or 'Dell XPS 15'_",
    "justification": "🤔 Could you clarify why you need this? A brief business reason helps the approval process.",
    "urgency":       "🤔 Please reply with exactly `HIGH`, `NORMAL`, or `LOW`.",
    "cost_estimate": "🤔 I couldn't parse that as a price. Try something like `1500`, `2k`, or `unknown`.",
}


# ─────────────────────────────────────────────────────────────────────────────
# Slot Machine
# ─────────────────────────────────────────────────────────────────────────────

class SlotMachine:
    """
    Finite-state conversation manager for a single asset request session.

    Usage (from ConversationHandler)
    ---------------------------------
        machine = SlotMachine(user_id=user_id)
        context.user_data["slot_machine"] = machine

        response = await machine.process(text)
        if machine.frozen:
            # End the conversation immediately
        elif machine.done:
            # Clean up, end conversation
    """

    def __init__(self, user_id: int, session_id: int = 0, user_identity: str = "") -> None:
        self.user_id       = user_id
        self.session_id    = session_id
        self.user_identity = user_identity
        self.state         = ConversationState.COLLECTING
        self.slots: Dict[str, Any] = {}
        # Retry tracker: how many times each slot has been re-asked
        self._retries: Dict[str, int] = {s: 0 for s in _SLOT_NAMES}
        # Last extraction result (exposed for debugging / admin logs)
        self.last_result: Optional[ExtractionResult] = None

    # ── Public interface ──────────────────────────────────────────────────────

    @property
    def frozen(self) -> bool:
        return self.state == ConversationState.FROZEN

    @property
    def done(self) -> bool:
        return self.state == ConversationState.DONE

    @property
    def active_slot(self) -> Optional[str]:
        """Return the name of the slot currently being collected."""
        for name in _SLOT_NAMES:
            if name not in self.slots:
                return name
        return None

    async def process(self, text: str) -> str:
        """
        Main entry-point: route text to the correct state handler.

        Always returns a string reply for the bot to send.
        Callers should check `.frozen` and `.done` after each call.
        """
        if self.state == ConversationState.FROZEN:
            return (
                "🔒 *This session has been frozen by MUGEN AI's security system.*\n"
                "Start a fresh request with /request — suspicious activity has been logged."
            )
        if self.state == ConversationState.DONE:
            return "✅ Your request has already been submitted. Use /request to start a new one."
        if self.state == ConversationState.COLLECTING:
            return await self._collect(text)
        if self.state == ConversationState.CONFIRMING:
            return await self._confirm(text)
        if self.state == ConversationState.DECIDING:
            return "⏳ Your request is being evaluated… please wait."

        return "❓ Unexpected state. Use /cancel to reset."

    def get_opening_prompt(self) -> str:
        """Return the prompt for the first slot (used after /request)."""
        return _SLOT_PROMPT_MAP["asset_name"]

    # ── State handlers ────────────────────────────────────────────────────────

    async def _collect(self, text: str) -> str:
        """Extract the current active slot, apply confidence gating."""
        slot = self.active_slot
        if slot is None:
            # All slots filled — advance to confirmation
            self.state = ConversationState.CONFIRMING
            return self._build_summary()

        result = await extract_slot(slot_name=slot, text=text)
        self.last_result = result

        # ── 🚨 Injection risk: HIGH → freeze immediately ───────────────────────
        if result.injection_risk == "high":
            return await self._freeze(result)

        # ── Low risk warning (non-blocking) ───────────────────────────────────
        if result.injection_risk == "low":
            log.warning(
                "low_injection_risk_flagged",
                user_id=self.user_id,
                slot=slot,
                snippet=text[:100],
            )
            asyncio.create_task(self._log_security("LOW_RISK", result))

        # ── Confidence gating ─────────────────────────────────────────────────
        if result.accepted:
            # ✅ Good extraction — store the slot value
            corrected_notice = ""
            if result.corrected_text:
                corrected_notice = (
                    f"\n✏️ _(I interpreted that as: *{result.corrected_text}*)_"
                )

            self.slots[slot] = result.value
            self._retries[slot] = 0

            # Move to next slot or confirmation
            next_slot = self.active_slot
            if next_slot is None:
                self.state = ConversationState.CONFIRMING
                return corrected_notice + "\n\n" + self._build_summary() if corrected_notice else self._build_summary()

            return corrected_notice + "\n\n" + _SLOT_PROMPT_MAP[next_slot] if corrected_notice else _SLOT_PROMPT_MAP[next_slot]

        # ── Below threshold ───────────────────────────────────────────────────
        self._retries[slot] = self._retries.get(slot, 0) + 1

        if self._retries[slot] >= MAX_RETRIES_PER_SLOT:
            # Skip slot after max retries (use None as default)
            log.warning("slot_max_retries_reached", slot=slot, user_id=self.user_id)
            self.slots[slot] = None
            self._retries[slot] = 0
            next_slot = self.active_slot
            if next_slot is None:
                self.state = ConversationState.CONFIRMING
                return self._build_summary()
            return (
                f"⏭️ _{slot.replace('_', ' ').title()} skipped after multiple attempts._\n\n"
                + _SLOT_PROMPT_MAP[next_slot]
            )

        # Re-ask based on confidence band
        if result.confidence >= 0.40:
            # Low-confidence — give a helpful hint
            return (
                f"🔍 _(Confidence: {result.confidence:.0%} — let me double-check)_\n\n"
                + _LOW_CONF_HINT[slot]
            )
        else:
            # Very low — standard re-ask
            return (
                f"❓ I couldn't extract that. Let's try again.\n\n"
                + _SLOT_PROMPT_MAP[slot]
            )

    async def _confirm(self, text: str) -> str:
        """Parse yes/no and either proceed to decision or reset."""
        lower = text.lower().strip()
        yes = any(w in lower for w in ["yes", "confirm", "ok", "proceed", "y", "sure", "go", "submit"])
        no  = any(w in lower for w in ["no", "cancel", "abort", "n", "stop", "restart", "reset"])

        if yes:
            self.state = ConversationState.DECIDING
            return await self._run_decision()

        if no:
            self.state = ConversationState.COLLECTING
            self.slots.clear()
            self._retries = {s: 0 for s in _SLOT_NAMES}
            return "🔄 *Request reset.* Let's start fresh.\n\n" + _SLOT_PROMPT_MAP["asset_name"]

        return (
            "❓ Please reply with *Yes* to submit or *No* to restart.\n\n"
            + self._build_summary()
        )

    async def _run_decision(self) -> str:
        """Run HRIS rule-based validation and save result to SQLite."""
        try:
            from bot.db.repository import append_audit, create_request, update_request_decision
            from bot.validation.hris_check import evaluate_request

            # Save request to SQLite first
            req_id = await create_request(
                session_id=self.session_id,
                user_id=self.user_id,
                slots=self.slots,
            )

            # Instant HRIS rule-based decision (no LLM, no network call)
            decision = evaluate_request(self.slots, user_id=self.user_id, user_identity=self.user_identity)

            # Persist decision back to SQLite
            await update_request_decision(
                request_id=req_id,
                status=decision.status,
                reason=decision.reason,
                policy_refs=decision.policy_refs,
                suggested_alternative=None,
                employee_grade=decision.employee_grade,
                rag_signal="NONE",
            )
            await append_audit(
                req_id,
                actor="MUGEN_AI",
                action=decision.status,
                detail=decision.reason,
            )

            self.state = ConversationState.DONE
            return decision.format_telegram(req_id)

        except Exception as exc:
            log.error("decision_failed", error=str(exc), user_id=self.user_id)
            self.state = ConversationState.DONE
            return (
                "❌ An error occurred while processing your request.\n"
                "Please try again with /request."
            )

    # ── Security helpers ──────────────────────────────────────────────────────

    async def _freeze(self, result: ExtractionResult) -> str:
        """
        Transition to FROZEN state and log the security event.
        Called when injection_risk == "high" is detected during slot extraction.
        """
        self.state = ConversationState.FROZEN
        log.critical(
            "session_frozen_injection_detected",
            user_id=self.user_id,
            session_id=self.session_id,
            slot=result.slot_name,
            snippet=result.raw_input[:120],
        )
        asyncio.create_task(self._log_security("INJECTION_FREEZE", result))

        return (
            "🔒 *Session Frozen — Security Alert*\n\n"
            "MUGEN AI's NLP layer detected a potential prompt-injection or "
            "policy-bypass attempt in your last message.\n\n"
            "This session has been *permanently frozen* and the event has "
            "been logged for administrator review.\n\n"
            "If this was a mistake, please contact your IT administrator.\n\n"
            "🆔 `FREEZE-{uid}`".format(uid=self.user_id)
        )

    async def _log_security(self, event_type: str, result: ExtractionResult) -> None:
        try:
            from bot.db.repository import log_security_event
            await log_security_event(
                user_id=self.user_id,
                event_type=event_type,
                score=result.confidence,
                signals={
                    "injection_risk": result.injection_risk,
                    "slot": result.slot_name,
                    "confidence": result.confidence,
                },
                snippet=result.raw_input[:500],
            )
        except Exception as exc:
            log.error("security_log_failed", error=str(exc))

    # ── UI helpers ────────────────────────────────────────────────────────────

    def _build_summary(self) -> str:
        cost = self.slots.get("cost_estimate")
        cost_str = f"${cost:,.0f}" if isinstance(cost, (int, float)) else (str(cost) if cost else "Unknown")

        urgency_icon = {"HIGH": "🔴", "NORMAL": "🟡", "LOW": "🟢"}.get(
            str(self.slots.get("urgency", "")).upper(), "⚪"
        )

        return (
            "📋 *Request Summary — please review before submitting*\n\n"
            f"🖥️  Asset      : `{self.slots.get('asset_name') or '—'}`\n"
            f"📝  Reason     : _{self.slots.get('justification') or '—'}_\n"
            f"{urgency_icon}  Urgency    : `{self.slots.get('urgency') or '—'}`\n"
            f"💰  Est. Cost  : `{cost_str}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Reply *Yes* to submit · *No* to restart"
        )
