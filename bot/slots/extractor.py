"""
bot/slots/extractor.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — LLM-Powered Slot Extractor
══════════════════════════════════════════════════════════════════════════════
Uses Groq (LLaMA 3.3 70B) via LangChain LCEL to extract structured asset-
request slots from unstructured natural language.

The prompt is carefully calibrated to:
  • Extract multiple slots from a single message
  • Handle currency phrases ("around 2k", "~$1500")
  • Normalise urgency to HIGH/NORMAL/LOW
  • Return null for slots that aren't mentioned (never hallucinate)
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

import structlog
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from bot.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

# ─────────────────────────────────────────────────────────────────────────────
# LangChain LCEL chain
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM = """You are a slot extractor for an enterprise IT asset request system.
Extract the following fields from the user message. If a field is not mentioned, return null.

Fields:
- asset_name: The specific product/model requested (string or null)
- justification: Business reason for the request (string or null)
- urgency: One of HIGH, NORMAL, LOW (string or null)
- cost_estimate: Numeric USD estimate — convert phrases like "2k"→2000, "~$1500"→1500 (number or null)

Current slot being filled: {current_slot}

Respond ONLY with valid JSON. Example:
{{"asset_name": "MacBook Pro 14", "justification": null, "urgency": "HIGH", "cost_estimate": 2499}}
"""

_HUMAN = "User message: {text}"

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human",  _HUMAN),
])

_llm = ChatGroq(
    api_key=settings.groq_api_key,
    model=settings.groq_model,
    temperature=0.0,
    max_tokens=256,
)

_chain = _prompt | _llm | JsonOutputParser()

# ─────────────────────────────────────────────────────────────────────────────
# Regex fallbacks (fast path for obvious patterns)
# ─────────────────────────────────────────────────────────────────────────────

_URGENCY_MAP = {
    r"\b(high|urgent|asap|critical|immediately)\b": "HIGH",
    r"\b(low|whenever|no\s+rush|not\s+urgent)\b":   "LOW",
    r"\b(normal|medium|standard|regular)\b":         "NORMAL",
}

_COST_PATTERN = re.compile(
    r"\$?\s*(\d[\d,]*(?:\.\d{1,2})?)\s*k?\b|\b(\d+)\s*k\b",
    re.IGNORECASE,
)


def _regex_urgency(text: str) -> Optional[str]:
    lower = text.lower()
    for pattern, label in _URGENCY_MAP.items():
        if re.search(pattern, lower):
            return label
    return None


def _regex_cost(text: str) -> Optional[float]:
    m = _COST_PATTERN.search(text)
    if not m:
        return None
    raw = (m.group(1) or m.group(2) or "").replace(",", "")
    try:
        val = float(raw)
        # Detect "k" suffix
        if re.search(r"\d\s*k\b", m.group(0), re.IGNORECASE):
            val *= 1000
        return val
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def extract_slots(
    text: str, current_slot: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract slot values from user text.

    Falls back to regex-only extraction on LLM error to maintain resilience.
    """
    # ── Try LLM first ─────────────────────────────────────────────────────────
    try:
        result: Dict[str, Any] = await _chain.ainvoke({
            "text": text[:1000],
            "current_slot": current_slot or "any",
        })
        # Normalise urgency
        if result.get("urgency"):
            result["urgency"] = str(result["urgency"]).upper()
            if result["urgency"] not in ("HIGH", "NORMAL", "LOW"):
                result["urgency"] = None
        # Normalise cost
        if result.get("cost_estimate") is not None:
            try:
                result["cost_estimate"] = float(result["cost_estimate"])
            except (TypeError, ValueError):
                result["cost_estimate"] = None
        return result

    except Exception as exc:
        log.warning("slot_extractor_llm_failed", error=str(exc))

    # ── Regex fallback ────────────────────────────────────────────────────────
    return {
        "asset_name":     None,   # Cannot reliably regex-extract free-form names
        "justification":  None,
        "urgency":        _regex_urgency(text),
        "cost_estimate":  _regex_cost(text),
    }
