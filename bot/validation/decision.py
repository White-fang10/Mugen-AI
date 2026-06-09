"""
bot/validation/decision.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — LLM Decision Engine
══════════════════════════════════════════════════════════════════════════════
Evaluates a completed asset request against:
  1. Live RAG context from uploaded policy PDFs
  2. The static asset_policy.json ruleset (cost limits, category rules)
  3. HRIS data (employee role, tenure, budget entitlement)

Returns a rich Verdict Pydantic model consumed by the slot machine.

Decision outcomes
─────────────────
  APPROVED      — Compliant, within budget, no flags
  NEEDS_REVIEW  — Borderline (requires manager sign-off)
  REJECTED      — Policy violation or over budget
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from bot.config import get_settings
from bot.rag.retriever import retrieve_policy

log = structlog.get_logger(__name__)
settings = get_settings()

# ─────────────────────────────────────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────────────────────────────────────

class Verdict(BaseModel):
    status: str            # APPROVED | NEEDS_REVIEW | REJECTED
    reason: str
    policy_refs: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)


# ─────────────────────────────────────────────────────────────────────────────
# Static data loaders
# ─────────────────────────────────────────────────────────────────────────────

_DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _load_json(name: str) -> Any:
    p = _DATA_DIR / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# LangChain LCEL decision chain
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM = """You are MUGEN AI's policy decision engine for an enterprise asset request system.

You will receive:
1. The asset request details (structured JSON)
2. Relevant policy excerpts retrieved from the company rulebook (RAG context)
3. Static policy rules (JSON)

Your job: decide whether to APPROVE, flag for NEEDS_REVIEW, or REJECT the request.

Rules:
- APPROVE if: within budget, justified, policy-compliant
- NEEDS_REVIEW if: borderline cost, unusual asset, or requires manager approval per policy
- REJECT if: clearly over budget, policy violation, or unjustified

Respond ONLY in this JSON format:
{{
  "status": "APPROVED" | "NEEDS_REVIEW" | "REJECTED",
  "reason": "Detailed explanation referencing specific policy points",
  "policy_refs": ["relevant policy section or excerpt"],
  "confidence": 0.0-1.0
}}
"""

_HUMAN = """
Asset Request:
{request_json}

RAG Policy Context:
{rag_context}

Static Policy Rules:
{static_policy}
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human",  _HUMAN),
])

_llm = ChatGroq(
    api_key=settings.groq_api_key,
    model=settings.groq_model,
    temperature=0.1,
    max_tokens=512,
)

_chain = _prompt | _llm | JsonOutputParser()


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def evaluate_request(slots: Dict[str, Any]) -> Verdict:
    """
    Run full policy evaluation for a completed asset request.

    Parameters
    ----------
    slots : dict
        Keys: asset_name, justification, urgency, cost_estimate

    Returns
    -------
    Verdict
    """
    # ── Pull RAG context ──────────────────────────────────────────────────────
    query = f"{slots.get('asset_name', '')} {slots.get('justification', '')}"
    rag_hits = await retrieve_policy(query)
    rag_context = "\n\n".join(
        f"[Source: {src}]\n{text}" for text, src in rag_hits
    ) or "No policy documents indexed yet."

    # ── Load static rules ─────────────────────────────────────────────────────
    static_policy = _load_json("asset_policy.json")
    products      = _load_json("products.json")

    # Enrich slots with product data if available
    asset_name = slots.get("asset_name", "")
    matched_product = next(
        (p for p in products.get("products", [])
         if asset_name.lower() in p.get("name", "").lower()),
        None
    )
    if matched_product and slots.get("cost_estimate") is None:
        slots = {**slots, "cost_estimate": matched_product.get("msrp")}

    # ── Invoke decision chain ─────────────────────────────────────────────────
    try:
        raw: Dict[str, Any] = await _chain.ainvoke({
            "request_json":  json.dumps(slots, indent=2),
            "rag_context":   rag_context,
            "static_policy": json.dumps(static_policy, indent=2),
        })

        return Verdict(
            status=raw.get("status", "NEEDS_REVIEW"),
            reason=raw.get("reason", "Decision engine produced no reason."),
            policy_refs=raw.get("policy_refs", []),
            confidence=float(raw.get("confidence", 0.7)),
        )

    except Exception as exc:
        log.error("decision_engine_failed", error=str(exc))
        return Verdict(
            status="NEEDS_REVIEW",
            reason="Automated decision engine encountered an error. Escalated for manual review.",
            policy_refs=[],
            confidence=0.0,
        )
