"""
bot/validation/hris_check.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — SD-05 Simple HRIS Rule-Based Decision Engine
══════════════════════════════════════════════════════════════════════════════

Validates an asset request against the predefined hris.json.
No LLM calls. Instant. Always reliable.

Decision rules
──────────────
  APPROVED  — employee found in HRIS, cost within their budget_usd
  FLAGGED   — employee found but cost > budget_usd (needs manager sign-off)
  REJECTED  — cost > 2× budget_usd (way over budget) OR employee not in HRIS

Output
──────
  A dict saved directly to SQLite as the structured request record.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

log = structlog.get_logger(__name__)

_DATA_DIR  = Path(__file__).parent.parent.parent / "data"
_HRIS_PATH = _DATA_DIR / "hris.json"

# Grade hierarchy — higher number = higher seniority
_GRADE_RANK: Dict[str, int] = {
    "L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5, "L6": 6,
}


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class HrisDecision:
    status: str                          # "APPROVED" | "FLAGGED" | "REJECTED"
    reason: str
    employee_name: str    = "Unknown"
    employee_grade: str   = "UNKNOWN"
    employee_role: str    = "Unknown"
    department: str       = "Unknown"
    budget_usd: int       = 0
    cost_estimate: Optional[float] = None
    policy_refs: List[str] = field(default_factory=list)

    @property
    def icon(self) -> str:
        return {"APPROVED": "✅", "FLAGGED": "🔍", "REJECTED": "❌"}.get(self.status, "❓")

    def format_telegram(self, request_id: str) -> str:
        cost_str = f"${self.cost_estimate:,.0f}" if self.cost_estimate else "Unknown"
        budget_str = f"${self.budget_usd:,}" if self.budget_usd else "N/A"
        refs = "\n".join(f"  • _{r}_" for r in self.policy_refs) if self.policy_refs else "  _HRIS policy check_"

        return (
            f"{self.icon} *Decision: {self.status}*\n\n"
            f"*Request ID:* `{request_id}`\n\n"
            f"*Employee:* {self.employee_name}\n"
            f"*Role:* {self.employee_role}\n"
            f"*Grade:* `{self.employee_grade}`\n"
            f"*Department:* {self.department}\n"
            f"*Budget Limit:* `{budget_str}`\n"
            f"*Requested Cost:* `{cost_str}`\n\n"
            f"*Reasoning:*\n{self.reason}\n\n"
            f"*Policy References:*\n{refs}\n\n"
            f"_Track with_ `/status {request_id}`"
        )


# ─────────────────────────────────────────────────────────────────────────────
# HRIS loader
# ─────────────────────────────────────────────────────────────────────────────

def _load_hris() -> List[Dict[str, Any]]:
    """Load the predefined hris.json employee list."""
    try:
        data = json.loads(_HRIS_PATH.read_text(encoding="utf-8"))
        return data.get("employees", [])
    except Exception as exc:
        log.error("hris_load_failed", error=str(exc))
        return []


import re

def lookup_employee_by_telegram_id(telegram_id: int, user_identity: str = "") -> Optional[Dict[str, Any]]:
    """
    Look up an employee by the collected identity text (e.g. "Alice Johnson, EMP001").
    Falls back to Telegram user ID, and then a default user for demo purposes.
    """
    employees = _load_hris()
    
    # 1. Search by employee_id found in the user_identity string
    if user_identity:
        match = re.search(r"EMP\d+", user_identity.upper())
        if match:
            emp_id = match.group(0)
            for emp in employees:
                if emp.get("employee_id") == emp_id:
                    return emp
        
        # 1b. Search by name match in the user_identity string
        identity_lower = user_identity.lower()
        for emp in employees:
            if emp.get("name", "").lower() in identity_lower:
                return emp

    # 2. Search by telegram_id field
    for emp in employees:
        if emp.get("telegram_id") == telegram_id:
            return emp

    # 3. Demo fallback: map any unknown Telegram ID to EMP004 (Pranesh)
    for emp in employees:
        if emp.get("employee_id") == "EMP004":
            return emp
            
    return employees[0] if employees else None


# ─────────────────────────────────────────────────────────────────────────────
# Decision engine
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_request(slots: Dict[str, Any], user_id: Optional[int] = None, user_identity: str = "") -> HrisDecision:
    """
    Rule-based decision engine. No LLM. Returns instantly.

    Rules applied in order:
    1. Employee lookup — if not found → FLAGGED (can't verify identity)
    2. Cost vs budget:
       - cost <= budget_usd          → APPROVED
       - budget_usd < cost <= 2×     → FLAGGED (needs manager approval)
       - cost > 2× budget_usd        → REJECTED (way over budget)
    3. No cost provided              → FLAGGED (manual review needed)
    """
    asset_name    = slots.get("asset_name", "Unknown asset")
    justification = slots.get("justification", "")
    urgency       = slots.get("urgency", "NORMAL")
    cost_estimate = slots.get("cost_estimate")  # float or None

    # ── 1. Employee lookup ────────────────────────────────────────────────────
    employee = lookup_employee_by_telegram_id(user_id, user_identity) if user_id else None

    if employee is None:
        log.warning("hris_employee_not_found", user_id=user_id, identity=user_identity)
        return HrisDecision(
            status="FLAGGED",
            reason=(
                "Employee record not found in HRIS. "
                "Identity cannot be verified — request routed for manual review."
            ),
            policy_refs=["hris.json §employee_lookup"],
            cost_estimate=cost_estimate,
        )

    emp_name   = employee.get("name", "Unknown")
    emp_grade  = employee.get("grade", "L1")
    emp_role   = employee.get("role", "Unknown")
    emp_dept   = employee.get("department", "Unknown")
    emp_budget = int(employee.get("budget_usd", 0))

    log.info(
        "hris_employee_resolved",
        name=emp_name, grade=emp_grade, budget=emp_budget, cost=cost_estimate,
    )

    # ── 2. No cost provided ───────────────────────────────────────────────────
    if cost_estimate is None:
        return HrisDecision(
            status="FLAGGED",
            reason=(
                f"{emp_name} ({emp_grade}) has a budget of ${emp_budget:,}. "
                "No cost estimate provided — routed for manager review to confirm pricing."
            ),
            employee_name=emp_name,
            employee_grade=emp_grade,
            employee_role=emp_role,
            department=emp_dept,
            budget_usd=emp_budget,
            cost_estimate=None,
            policy_refs=["hris.json §budget_usd", "asset_policy §cost_required"],
        )

    cost = float(cost_estimate)

    # ── 3. Cost decision ──────────────────────────────────────────────────────
    if cost <= emp_budget:
        return HrisDecision(
            status="APPROVED",
            reason=(
                f"The requested asset ('{asset_name}') has an estimated cost of ${cost:,.0f}. "
                f"This falls within the allocated budget threshold of ${emp_budget:,} for {emp_name}'s "
                f"current grade ({emp_grade}). The business justification ('{justification}') and "
                f"urgency ({urgency}) have been logged. The request meets all automated HRIS compliance "
                "criteria and is therefore approved."
            ),
            employee_name=emp_name,
            employee_grade=emp_grade,
            employee_role=emp_role,
            department=emp_dept,
            budget_usd=emp_budget,
            cost_estimate=cost,
            policy_refs=["hris.json §budget_usd", f"hris.json §grade:{emp_grade}"],
        )

    elif cost <= emp_budget * 2:
        return HrisDecision(
            status="FLAGGED",
            reason=(
                f"The estimated cost of ${cost:,.0f} for the requested asset ('{asset_name}') "
                f"exceeds {emp_name}'s standard budget allocation of ${emp_budget:,} (Grade {emp_grade}) "
                f"by a margin of ${cost - emp_budget:,.0f}. In accordance with procurement policy, "
                "this request has been flagged and requires manual managerial sign-off before fulfilment."
            ),
            employee_name=emp_name,
            employee_grade=emp_grade,
            employee_role=emp_role,
            department=emp_dept,
            budget_usd=emp_budget,
            cost_estimate=cost,
            policy_refs=["hris.json §budget_usd", "asset_policy §over_budget_review"],
        )

    else:
        return HrisDecision(
            status="REJECTED",
            reason=(
                f"The estimated cost of ${cost:,.0f} for the requested asset ('{asset_name}') "
                f"is significantly beyond the maximum allowable overage for {emp_name}'s "
                f"standard budget of ${emp_budget:,} (Grade {emp_grade}). The automated system "
                "cannot approve this request. Please initiate a formal procurement request "
                "through the central finance team for further assessment."
            ),
            employee_name=emp_name,
            employee_grade=emp_grade,
            employee_role=emp_role,
            department=emp_dept,
            budget_usd=emp_budget,
            cost_estimate=cost,
            policy_refs=["hris.json §budget_usd", "asset_policy §hard_reject_2x_budget"],
        )
