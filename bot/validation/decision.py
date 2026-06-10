"""
bot/validation/decision.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — Stage 4: Full Decision Engine
══════════════════════════════════════════════════════════════════════════════

What's new in Stage 4
──────────────────────
  • HRIS integration — employee grade, budget, tenure pulled into every prompt
  • Product catalogue context — stock count, price, min_grade for requested item
  • Grade eligibility check — pre-LLM hard reject if employee grade < min_grade
  • suggested_alternative — if rejected/out-of-stock, LLM picks best in-stock,
    in-budget, grade-eligible alternative from the catalogue
  • Enriched Verdict model: status is now "approved" | "flagged" | "rejected"
    (lowercase, human-friendly) with legacy uppercase mapping for DB storage
  • Over-budget pre-screen — if cost > employee budget, status nudged to "flagged"
    before LLM call so the LLM reasons about an already-flagged context

Prompt architecture
────────────────────
  The LLM receives FOUR context blocks in this order:

  ╔═══════════════════════╗
  ║  1. EMPLOYEE (HRIS)   ║  name, role, grade, budget, tenure
  ╠═══════════════════════╣
  ║  2. ASSET REQUEST     ║  all slots + cost enrichment note
  ╠═══════════════════════╣
  ║  3. PRODUCT CONTEXT   ║  matched catalogue entry + alternatives
  ╠═══════════════════════╣
  ║  4. RAG POLICY CHUNKS ║  top-3 graded excerpts from company PDFs
  ╠═══════════════════════╣
  ║  5. STATIC POLICY     ║  asset_policy.json hard rules
  ╚═══════════════════════╝

LLM output schema
──────────────────
  {
    "status": "approved" | "flagged" | "rejected",
    "reason": "<cite specific rulebook clause or policy section>",
    "suggested_alternative": "<product name (price)>" | null,
    "policy_refs": ["<source p.N>", "§policy_section"],
    "confidence": 0.0–1.0
  }
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
from pydantic import BaseModel, Field, field_validator

from bot.config import get_settings
from bot.rag.retriever import RagContext, has_rulebook, retrieve_for_request
from bot.validation.hris import (
    employee_context_block,
    employee_meets_min_grade,
    get_employee_grade,
    lookup_employee,
)

log      = structlog.get_logger(__name__)
settings = get_settings()

_DATA_DIR = Path(__file__).parent.parent.parent / "data"

# ─────────────────────────────────────────────────────────────────────────────
# Verdict model
# ─────────────────────────────────────────────────────────────────────────────

_STATUS_DISPLAY = {
    "approved":  ("✅", "APPROVED"),
    "flagged":   ("🔍", "NEEDS_REVIEW"),
    "rejected":  ("❌", "REJECTED"),
}

class Verdict(BaseModel):
    """Rich decision result returned to the slot machine and stored in DB."""

    # ── Core decision ─────────────────────────────────────────────────────────
    status:               str                        # "approved"|"flagged"|"rejected"
    reason:               str
    suggested_alternative: Optional[str] = None      # product name + price, or None
    policy_refs:          List[str]      = Field(default_factory=list)
    confidence:           float          = Field(ge=0.0, le=1.0, default=0.8)

    # ── Metadata injected by evaluate_request ─────────────────────────────────
    rag_signal:           str            = "NONE"    # STRONG | WEAK | NONE
    source_citations:     List[str]      = Field(default_factory=list)
    employee_grade:       str            = "UNKNOWN"
    pre_screened:         bool           = False      # True if hard-rejected before LLM

    @field_validator("status", mode="before")
    @classmethod
    def _normalise_status(cls, v: object) -> str:
        v = str(v).lower().strip()
        return v if v in ("approved", "flagged", "rejected") else "flagged"

    # ── Display helpers ───────────────────────────────────────────────────────
    @property
    def db_status(self) -> str:
        """Uppercase string for DB storage (backward compatible)."""
        return _STATUS_DISPLAY.get(self.status, ("❓", "NEEDS_REVIEW"))[1]

    @property
    def icon(self) -> str:
        return _STATUS_DISPLAY.get(self.status, ("❓", "NEEDS_REVIEW"))[0]

    @property
    def confidence_bar(self) -> str:
        filled = int(self.confidence * 10)
        return "█" * filled + "░" * (10 - filled)

    def format_telegram(self, request_id: str) -> str:
        """Render the full verdict as a Telegram Markdown message."""
        refs = (
            "\n".join(f"  • _{r}_" for r in self.policy_refs)
            if self.policy_refs else "  _No specific clauses cited._"
        )
        alt_block = (
            f"\n💡 *Suggested Alternative:*\n  _{self.suggested_alternative}_"
            if self.suggested_alternative else ""
        )
        rag_badge = (
            "🟢 Strong policy signal"
            if self.rag_signal == "STRONG"
            else "🟡 Weak policy signal"
            if self.rag_signal == "WEAK"
            else "⚪ No rulebook indexed"
        )

        return (
            f"{self.icon} *Decision: {self.status.upper()}*\n\n"
            f"*Request ID:*  `{request_id}`\n"
            f"*Confidence:*  `{self.confidence_bar}` {self.confidence:.0%}\n"
            f"*RAG Signal:*  {rag_badge}\n"
            f"*Employee Grade:* `{self.employee_grade}`\n\n"
            f"*Reasoning:*\n{self.reason}"
            + alt_block
            + f"\n\n*Policy References:*\n{refs}\n\n"
            f"_Track with_ `/status {request_id}`"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Data helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_json(name: str) -> Any:
    p = _DATA_DIR / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _find_product(asset_name: str, products: List[Dict]) -> Optional[Dict]:
    """Exact-ish catalogue match (case-insensitive substring)."""
    name_lower = asset_name.lower()
    return next(
        (p for p in products if name_lower in p.get("name", "").lower()),
        None,
    )


def _find_alternatives(
    category: str,
    max_price: float,
    min_grade_rank: int,
    grade_hierarchy: Dict[str, int],
    products: List[Dict],
    exclude_id: str = "",
) -> List[Dict]:
    """
    Find in-stock, in-budget, grade-eligible alternatives in the same category.
    Returns up to 3, sorted by price ascending.
    """
    alts = [
        p for p in products
        if (
            p.get("category") == category
            and p.get("stock_count", 0) > 0
            and p.get("price", 9999999) <= max_price
            and grade_hierarchy.get(p.get("min_grade", "IC1"), 0) <= min_grade_rank
            and p.get("id") != exclude_id
        )
    ]
    alts.sort(key=lambda p: p.get("price", 0))
    return alts[:3]


def _product_context_block(
    asset_name: str,
    matched: Optional[Dict],
    alternatives: List[Dict],
    employee: Optional[Dict],
) -> str:
    """Format the product context block for the LLM prompt."""
    if matched is None:
        alt_lines = "\n".join(
            f"  • {a['name']} — ${a['price']:,} "
            f"(stock: {a['stock_count']}, min_grade: {a['min_grade']})"
            for a in alternatives
        ) or "  None available within budget and grade."
        return (
            f"Requested product : '{asset_name}' — NOT FOUND in catalogue\n"
            f"Eligible alternatives:\n{alt_lines}"
        )

    in_stock_str  = f"{matched['stock_count']} in stock" if matched["stock_count"] > 0 else "⚠️ OUT OF STOCK"
    grade_ok      = ""
    if employee:
        from bot.validation.hris import employee_meets_min_grade
        ok = employee_meets_min_grade(employee, matched.get("min_grade", "IC1"))
        grade_ok = f"\nGrade eligible    : {'YES ✓' if ok else 'NO ✗ — employee grade below minimum'}"

    alt_lines = "\n".join(
        f"  • {a['name']} — ${a['price']:,} "
        f"(stock: {a['stock_count']}, min_grade: {a['min_grade']})"
        for a in alternatives
    ) or "  None available."

    return (
        f"Product ID        : {matched['id']}\n"
        f"Product Name      : {matched['name']}\n"
        f"Category          : {matched['category']}\n"
        f"Vendor            : {matched['vendor']}\n"
        f"Catalogue Price   : ${matched['price']:,}\n"
        f"Stock             : {in_stock_str}\n"
        f"Min Grade Required: {matched.get('min_grade', 'IC1')}\n"
        f"Description       : {matched.get('description', '')}"
        + grade_ok
        + f"\n\nIn-stock alternatives (same category):\n{alt_lines}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# LLM decision chain (Stage 4 prompt)
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM = """\
You are MUGEN AI's policy decision engine for an enterprise IT asset request system.
You receive structured context in five blocks and must produce a single fair decision.

━━━ DECISION RULES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"approved"  — Employee is eligible by grade, request is within their budget,
              asset is in-stock, and no policy rules prohibit it.

"flagged"   — One of: cost near/over budget but not egregious, asset is in-stock
              but requires manager approval, policy is ambiguous, tenure < 6 months
              on a high-value item. Requires human review before fulfilment.

"rejected"  — One or more hard blocks: employee grade below min_grade, asset is
              a prohibited item, cost exceeds global hard-reject limit, or
              asset category is not permitted for the employee's role.

━━━ SUGGESTED ALTERNATIVE RULES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If status is "rejected" or the requested product is out-of-stock, you MUST provide
a suggested_alternative from the "In-stock alternatives" list in the product context.
Choose the best fit (closest in category and function, within budget, grade-eligible).
Format: "Product Name — $price"
If no alternative exists, return null.

━━━ CITATION RULES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Always cite at least one specific source in policy_refs:
  • RAG chunks  → "source_filename p.N (Grade X)"
  • Static JSON → "asset_policy.json §section_name"
  • Catalogue   → "products.json #{product_id}"

━━━ OUTPUT FORMAT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Respond ONLY with this JSON (no markdown, no extra text):
{{
  "status": "approved" | "flagged" | "rejected",
  "reason": "Specific, policy-grounded explanation. Quote the rulebook or policy section.",
  "suggested_alternative": "Product Name — $price" | null,
  "policy_refs": ["asset_policy.json §laptop.max_usd", "rulebook.pdf p.12 (Grade A)"],
  "confidence": 0.0-1.0
}}
"""

_HUMAN = """\
━━━ 1. EMPLOYEE PROFILE (HRIS) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{employee_context}

━━━ 2. ASSET REQUEST (validated slots) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{request_json}

━━━ 3. PRODUCT CATALOGUE CONTEXT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{product_context}

━━━ 4. RAG POLICY CONTEXT (top-3 chunks, graded A–D) ━━━━━━━━━━━━━━━━━━━━━━━━━
{rag_context}

━━━ 5. STATIC POLICY RULES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{static_policy}
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human",  _HUMAN),
])

_llm = ChatGroq(
    api_key=settings.groq_api_key,
    model=settings.groq_model,
    temperature=0.05,
    max_tokens=700,
    timeout=15.0,
)

_chain = _prompt | _llm | JsonOutputParser()


# ─────────────────────────────────────────────────────────────────────────────
# Pre-screening (runs before LLM to catch hard violations cheaply)
# ─────────────────────────────────────────────────────────────────────────────

def _pre_screen(
    slots: Dict[str, Any],
    employee: Optional[Dict],
    matched_product: Optional[Dict],
    grade_hierarchy: Dict[str, int],
    static_policy: Dict,
) -> Optional[Verdict]:
    """
    Fast, rule-based pre-screen. Returns a Verdict immediately on hard violation.
    Returns None if the request should proceed to the LLM.
    """
    asset_name    = slots.get("asset_name", "")
    cost_estimate = slots.get("cost_estimate")
    emp_grade     = get_employee_grade(employee) if employee else "IC1"
    emp_budget    = employee.get("budget_usd", 0) if employee else 0

    # 1. Prohibited items check
    prohibited = [p.lower() for p in static_policy.get("prohibited_items", [])]
    if any(p in asset_name.lower() for p in prohibited):
        return Verdict(
            status="rejected",
            reason=(
                f"'{asset_name}' matches a prohibited item category "
                f"per asset_policy.json §prohibited_items. "
                "This asset type is not approved for company procurement."
            ),
            policy_refs=["asset_policy.json §prohibited_items"],
            confidence=0.99,
            pre_screened=True,
            employee_grade=emp_grade,
        )

    # 2. Global hard-reject limit
    global_rules    = static_policy.get("global_rules", {})
    hard_reject_usd = global_rules.get("hard_reject_limit_usd", 10000)
    if cost_estimate and cost_estimate > hard_reject_usd:
        return Verdict(
            status="rejected",
            reason=(
                f"Estimated cost ${cost_estimate:,.0f} exceeds the global hard-reject "
                f"limit of ${hard_reject_usd:,} per asset_policy.json §global_rules. "
                "Requires a separate procurement process and CTO approval."
            ),
            policy_refs=["asset_policy.json §global_rules.hard_reject_limit_usd"],
            confidence=0.99,
            pre_screened=True,
            employee_grade=emp_grade,
        )

    # 3. Grade eligibility for matched product
    if matched_product:
        min_grade = matched_product.get("min_grade", "IC1")
        if not employee_meets_min_grade(employee or {}, min_grade):
            return Verdict(
                status="rejected",
                reason=(
                    f"Employee grade {emp_grade} does not meet the minimum grade "
                    f"{min_grade} required for '{matched_product['name']}' "
                    f"per products.json #{matched_product['id']}."
                ),
                policy_refs=[f"products.json #{matched_product['id']} §min_grade"],
                confidence=0.97,
                pre_screened=True,
                employee_grade=emp_grade,
            )

    return None  # pass through to LLM


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def evaluate_request(
    slots: Dict[str, Any],
    user_id: Optional[int] = None,
) -> Verdict:
    """
    Run the full Stage 4 decision pipeline.

    Parameters
    ----------
    slots : dict
        Keys: asset_name, justification, urgency, cost_estimate
    user_id : int | None
        Telegram user ID — used to resolve the HRIS employee profile.

    Returns
    -------
    Verdict — always returns; falls back to "flagged" on any error.
    """
    asset_name    = slots.get("asset_name", "")
    justification = slots.get("justification", "")

    # ── 1. HRIS lookup ────────────────────────────────────────────────────────
    employee = lookup_employee(user_id) if user_id else None
    emp_grade = get_employee_grade(employee) if employee else "UNKNOWN"
    emp_block = employee_context_block(employee)

    log.info("hris_resolved", user_id=user_id, grade=emp_grade,
             budget=employee.get("budget_usd") if employee else None)

    # ── 2. Load catalogue ─────────────────────────────────────────────────────
    products_data  = _load_json("products.json")
    product_list   = products_data.get("catalog", [])
    grade_hierarchy = products_data.get("grade_hierarchy", {})
    static_policy  = _load_json("asset_policy.json")

    # ── 3. Match product + cost enrichment ────────────────────────────────────
    matched = _find_product(asset_name, product_list)
    if matched and slots.get("cost_estimate") is None:
        slots = {**slots, "cost_estimate": matched["price"], "_cost_source": "catalogue"}

    cost_estimate = slots.get("cost_estimate")
    emp_budget    = employee.get("budget_usd", 0) if employee else 0
    emp_grade_rank = grade_hierarchy.get(emp_grade, 0)

    # Build alternatives list (for use in product context and fallback)
    category    = matched.get("category", "") if matched else ""
    max_budget  = min(emp_budget, cost_estimate or emp_budget) if emp_budget else (cost_estimate or 9999999)
    alternatives = _find_alternatives(
        category=category or _guess_category(asset_name),
        max_price=emp_budget or max_budget,
        min_grade_rank=emp_grade_rank,
        grade_hierarchy=grade_hierarchy,
        products=product_list,
        exclude_id=matched.get("id", "") if matched else "",
    )

    product_block = _product_context_block(asset_name, matched, alternatives, employee)

    # ── 4. Pre-screen (fast rule checks before LLM) ───────────────────────────
    pre_verdict = _pre_screen(slots, employee, matched, grade_hierarchy, static_policy)
    if pre_verdict is not None:
        # Attach alternative if available
        if pre_verdict.status == "rejected" and alternatives and not pre_verdict.suggested_alternative:
            best = alternatives[0]
            pre_verdict.suggested_alternative = f"{best['name']} — ${best['price']:,}"
        pre_verdict.employee_grade = emp_grade
        log.info("pre_screened_verdict", status=pre_verdict.status, reason=pre_verdict.reason[:80])
        return pre_verdict

    # ── 5. RAG retrieval (top-3 graded) ──────────────────────────────────────
    rag_ctx: RagContext = await retrieve_for_request(
        asset_name=asset_name,
        justification=justification,
        k=3,
    )
    rag_signal = (
        "NONE"   if rag_ctx.empty else
        "STRONG" if rag_ctx.has_strong_signal else "WEAK"
    )

    # ── 6. Strip internal fields before LLM ───────────────────────────────────
    llm_slots = {k: v for k, v in slots.items() if not k.startswith("_")}

    # ── 7. Invoke Groq LLM ────────────────────────────────────────────────────
    try:
        raw: Dict[str, Any] = await _chain.ainvoke({
            "employee_context": emp_block,
            "request_json":     json.dumps(llm_slots, indent=2),
            "product_context":  product_block,
            "rag_context":      rag_ctx.to_llm_context(),
            "static_policy":    json.dumps(static_policy, indent=2),
        })

        # Merge citations
        policy_refs   = list(raw.get("policy_refs", []))
        rag_citations = rag_ctx.source_citations()
        combined_refs = policy_refs + [c for c in rag_citations if c not in policy_refs]

        verdict = Verdict(
            status=raw.get("status", "flagged"),
            reason=raw.get("reason", "No reason provided."),
            suggested_alternative=raw.get("suggested_alternative") or None,
            policy_refs=combined_refs,
            confidence=float(raw.get("confidence", 0.7)),
            rag_signal=rag_signal,
            source_citations=rag_citations,
            employee_grade=emp_grade,
        )

        log.info(
            "verdict_issued",
            status=verdict.status,
            confidence=verdict.confidence,
            rag_signal=rag_signal,
            alt=verdict.suggested_alternative,
            grade=emp_grade,
        )
        return verdict

    except Exception as exc:
        log.error("decision_engine_failed", error=str(exc))
        return Verdict(
            status="flagged",
            reason=(
                "The automated decision engine encountered an error. "
                "This request has been escalated for manual review."
            ),
            confidence=0.0,
            rag_signal=rag_signal,
            employee_grade=emp_grade,
        )


def _guess_category(asset_name: str) -> str:
    """Infer product category from asset name when no exact match found."""
    name = asset_name.lower()
    if any(w in name for w in ["laptop", "macbook", "thinkpad", "latitude", "notebook"]):
        return "laptop"
    if any(w in name for w in ["monitor", "display", "screen"]):
        return "monitor"
    if any(w in name for w in ["phone", "iphone", "galaxy", "pixel"]):
        return "mobile_phone"
    if any(w in name for w in ["headset", "headphone", "earphone", "airpod"]):
        return "headset"
    if any(w in name for w in ["keyboard"]):
        return "keyboard"
    if any(w in name for w in ["mouse"]):
        return "mouse"
    if any(w in name for w in ["license", "subscription", "software", "jetbrains", "adobe"]):
        return "software_license"
    return ""
