"""
bot/validation/decision.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — Stage 3: Upgraded LLM Decision Engine
══════════════════════════════════════════════════════════════════════════════

What changed from Stage 2
──────────────────────────
  • Uses retrieve_for_request() (returns RagContext) instead of
    retrieve_policy() (bare tuples). The graded, source-attributed context
    is injected into the LLM prompt so it can make more accurate citations.

  • rag_context.to_llm_context() produces a structured block with
    relevance grades (A–D) and page citations — the LLM is instructed
    to weight Grade-A/B chunks heavily and treat D-grades as weak signals.

  • Verdict now carries rag_signal (STRONG / WEAK / NONE) and
    source_citations from the RagContext, enabling richer Telegram replies.

  • Product catalogue lookup is enhanced to also search by category name
    so "laptop" → finds all laptops and uses the mean MSRP as guidance.

  • has_rulebook() check: if no PDFs indexed, the LLM is warned explicitly
    so it doesn't fabricate policy citations.

Decision outcomes
─────────────────
  APPROVED      — Within budget, justified, policy-compliant
  NEEDS_REVIEW  — Borderline cost, unusual asset, manager sign-off needed
  REJECTED      — Over budget, policy violation, or prohibited item
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from bot.config import get_settings
from bot.rag.retriever import RagContext, has_rulebook, retrieve_for_request

log = structlog.get_logger(__name__)
settings = get_settings()

# ─────────────────────────────────────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────────────────────────────────────

class Verdict(BaseModel):
    status:           str                        # APPROVED | NEEDS_REVIEW | REJECTED
    reason:           str
    policy_refs:      List[str] = Field(default_factory=list)
    confidence:       float     = Field(ge=0.0, le=1.0, default=0.8)
    rag_signal:       str       = "NONE"         # STRONG | WEAK | NONE
    source_citations: List[str] = Field(default_factory=list)

    @property
    def confidence_bar(self) -> str:
        filled = int(self.confidence * 10)
        return "█" * filled + "░" * (10 - filled)


# ─────────────────────────────────────────────────────────────────────────────
# Static data helpers
# ─────────────────────────────────────────────────────────────────────────────

_DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _load_json(name: str) -> Any:
    p = _DATA_DIR / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _enrich_cost(slots: Dict[str, Any], products: Dict[str, Any]) -> Dict[str, Any]:
    """
    If cost_estimate is missing, attempt to fill it from the product catalogue.

    Strategy:
      1. Exact name match (case-insensitive substring)
      2. Category match → mean MSRP of that category
    """
    if slots.get("cost_estimate") is not None:
        return slots   # already provided

    asset_name = (slots.get("asset_name") or "").lower()
    product_list = products.get("products", [])

    # Exact-ish match
    exact = next(
        (p for p in product_list if asset_name in p.get("name", "").lower()),
        None,
    )
    if exact:
        return {**slots, "cost_estimate": exact["msrp"], "_cost_source": "catalogue_exact"}

    # Category match
    category_match = [
        p["msrp"]
        for p in product_list
        if p.get("category", "") in asset_name or asset_name in p.get("category", "")
    ]
    if category_match:
        avg = round(statistics.mean(category_match), 2)
        return {**slots, "cost_estimate": avg, "_cost_source": "catalogue_category_avg"}

    return slots


# ─────────────────────────────────────────────────────────────────────────────
# Decision prompt — Stage 3 (graded RAG context injection)
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM = """\
You are MUGEN AI's policy decision engine for an enterprise IT asset request system.

You will receive:
1. ASSET REQUEST — structured JSON of what was requested
2. RAG POLICY CONTEXT — excerpts retrieved from company rulebooks,
   each tagged with a relevance grade (A = highly relevant, D = low relevance).
   Weight Grade-A and Grade-B chunks heavily. Treat Grade-D as weak signals only.
3. STATIC POLICY RULES — hard-coded cost caps and category rules (JSON)

Your task: produce a fair, policy-grounded decision.

Decision outcomes:
  APPROVED     — request is compliant: within budget, justified, policy-permitted
  NEEDS_REVIEW — borderline: cost near limit, unusual asset, or policy ambiguous
  REJECTED     — clear violation: over budget, prohibited item, policy denial

Important:
  - If RAG context says "No policy rulebooks indexed", base decision ONLY on static rules.
  - Always cite the specific policy rule or RAG source (source + page) in policy_refs.
  - Be precise in the reason — vague explanations are not acceptable.
  - confidence reflects YOUR certainty (1.0 = fully grounded in policy, 0.5 = educated guess).

Respond ONLY with this exact JSON (no markdown wrapper, no extra text):
{{
  "status": "APPROVED" | "NEEDS_REVIEW" | "REJECTED",
  "reason": "Detailed, specific explanation referencing policy clauses or RAG sources",
  "policy_refs": ["e.g. 'asset_policy.json § laptop.max_usd = $3500'", "e.g. 'rulebook.pdf p.12 — replacement cycle'"],
  "confidence": 0.0-1.0
}}
"""

_HUMAN = """\
━━━ 1. ASSET REQUEST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{request_json}

━━━ 2. RAG POLICY CONTEXT (top-3 chunks, graded) ━━━━━━━━━━━━━━━━━━━━━━━━━━
{rag_context}

━━━ 3. STATIC POLICY RULES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{static_policy}
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human",  _HUMAN),
])

_llm = ChatGroq(
    api_key=settings.groq_api_key,
    model=settings.groq_model,
    temperature=0.05,   # near-deterministic but slight variability for nuance
    max_tokens=600,
)

_chain = _prompt | _llm | JsonOutputParser()


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def evaluate_request(slots: Dict[str, Any]) -> Verdict:
    """
    Run full policy evaluation for a completed asset request.

    Flow:
      1. Enrich slots with catalogue cost estimate if missing
      2. Retrieve top-3 graded policy chunks via RAG
      3. Load static rules + product catalogue
      4. Invoke Groq LLM decision chain
      5. Return a Verdict with confidence bar and source citations

    Parameters
    ----------
    slots : dict
        Keys: asset_name, justification, urgency, cost_estimate

    Returns
    -------
    Verdict — always returns (never raises); falls back to NEEDS_REVIEW on error.
    """
    asset_name    = slots.get("asset_name", "")
    justification = slots.get("justification", "")

    # ── Step 1: Cost enrichment ───────────────────────────────────────────────
    products = _load_json("products.json")
    enriched_slots = _enrich_cost(slots, products)

    if enriched_slots.get("_cost_source"):
        log.info("cost_enriched", source=enriched_slots["_cost_source"], value=enriched_slots["cost_estimate"])

    # ── Step 2: RAG retrieval (top-3, graded) ─────────────────────────────────
    rag_ctx: RagContext = await retrieve_for_request(
        asset_name=asset_name,
        justification=justification,
        k=3,    # Stage 3 spec: top-3 chunks
    )

    rag_signal = (
        "NONE"   if rag_ctx.empty
        else "STRONG" if rag_ctx.has_strong_signal
        else "WEAK"
    )

    log.info(
        "rag_context_ready",
        signal=rag_signal,
        chunks=len(rag_ctx.chunks),
        grades=[c.grade for c in rag_ctx.chunks],
    )

    # ── Step 3: Load static rules ─────────────────────────────────────────────
    static_policy = _load_json("asset_policy.json")

    # Remove internal enrichment key before sending to LLM
    llm_slots = {k: v for k, v in enriched_slots.items() if not k.startswith("_")}

    # ── Step 4: Invoke LLM decision chain ─────────────────────────────────────
    try:
        raw: Dict[str, Any] = await _chain.ainvoke({
            "request_json":  json.dumps(llm_slots, indent=2),
            "rag_context":   rag_ctx.to_llm_context(),
            "static_policy": json.dumps(static_policy, indent=2),
        })

        # Merge RAG source citations into policy_refs
        policy_refs   = list(raw.get("policy_refs", []))
        rag_citations = rag_ctx.source_citations()
        combined_refs = policy_refs + [
            c for c in rag_citations if c not in policy_refs
        ]

        verdict = Verdict(
            status=raw.get("status", "NEEDS_REVIEW"),
            reason=raw.get("reason", "No reason provided by decision engine."),
            policy_refs=combined_refs,
            confidence=float(raw.get("confidence", 0.7)),
            rag_signal=rag_signal,
            source_citations=rag_citations,
        )

        log.info(
            "verdict_issued",
            status=verdict.status,
            confidence=verdict.confidence,
            rag_signal=rag_signal,
            refs=len(combined_refs),
        )
        return verdict

    except Exception as exc:
        log.error("decision_engine_failed", error=str(exc))
        return Verdict(
            status="NEEDS_REVIEW",
            reason=(
                "The automated decision engine encountered an error and could not "
                "complete evaluation. This request has been escalated for manual review."
            ),
            policy_refs=[],
            confidence=0.0,
            rag_signal=rag_signal,
        )
