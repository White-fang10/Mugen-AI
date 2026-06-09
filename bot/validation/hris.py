"""
bot/validation/hris.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — HRIS Employee Lookup
══════════════════════════════════════════════════════════════════════════════
Loads the mock HRIS roster from data/hris.json and provides:

  lookup_employee(user_id)   — map Telegram user_id → employee record
  get_employee_grade(record) — derive IC/M grade from role string
  employee_context_block()   — formatted string for LLM injection

In production this would call an HR API; the mock uses a deterministic
user_id % employee_count mapping so any valid Telegram user gets a
consistent employee profile for demo purposes.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

log = structlog.get_logger(__name__)

_DATA_DIR  = Path(__file__).parent.parent.parent / "data"
_HRIS_PATH = _DATA_DIR / "hris.json"
_PROD_PATH = _DATA_DIR / "products.json"


# ─────────────────────────────────────────────────────────────────────────────
# Data loaders (cached)
# ─────────────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_hris() -> list[Dict[str, Any]]:
    raw = json.loads(_HRIS_PATH.read_text(encoding="utf-8"))
    return raw.get("employees", [])


@lru_cache(maxsize=1)
def _load_role_grade_map() -> Dict[str, str]:
    raw = json.loads(_PROD_PATH.read_text(encoding="utf-8"))
    return raw.get("role_to_grade", {})


@lru_cache(maxsize=1)
def _load_grade_hierarchy() -> Dict[str, int]:
    raw = json.loads(_PROD_PATH.read_text(encoding="utf-8"))
    return raw.get("grade_hierarchy", {})


# ─────────────────────────────────────────────────────────────────────────────
# Grade helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_employee_grade(employee: Dict[str, Any]) -> str:
    """
    Derive the IC/M grade string from an employee's role field.
    Falls back to "IC2" if the role isn't in the mapping.
    """
    role  = employee.get("role", "")
    grade = _load_role_grade_map().get(role, "IC2")
    return grade


def grade_rank(grade: str) -> int:
    """Return a numeric rank for a grade string (higher = more senior)."""
    return _load_grade_hierarchy().get(grade, 0)


def employee_meets_min_grade(employee: Dict[str, Any], min_grade: str) -> bool:
    """Return True if the employee's grade is ≥ the product's min_grade."""
    emp_grade = get_employee_grade(employee)
    return grade_rank(emp_grade) >= grade_rank(min_grade)


# ─────────────────────────────────────────────────────────────────────────────
# Lookup
# ─────────────────────────────────────────────────────────────────────────────

def lookup_employee(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Look up an employee record by Telegram user_id.

    Strategy (mock):
      1. Check for an explicit "telegram_id" field match (future integration).
      2. Deterministic fallback: user_id % len(employees) → consistent demo profile.

    Returns None if the HRIS roster is empty.
    """
    employees = _load_hris()
    if not employees:
        return None

    # 1. Explicit mapping (production path)
    for emp in employees:
        if emp.get("telegram_id") == user_id:
            return emp

    # 2. Demo fallback — deterministic so the same user always gets same profile
    idx = user_id % len(employees)
    emp = dict(employees[idx])
    emp["_demo_mapping"] = True   # flag so logs can note it's a mock
    return emp


# ─────────────────────────────────────────────────────────────────────────────
# LLM context formatter
# ─────────────────────────────────────────────────────────────────────────────

def employee_context_block(employee: Optional[Dict[str, Any]]) -> str:
    """
    Format an employee record as a structured block for LLM injection.
    Returns a "HRIS unavailable" notice if employee is None.
    """
    if employee is None:
        return (
            "HRIS Status  : UNAVAILABLE\n"
            "Note         : No employee record found. Apply most restrictive policy defaults.\n"
            "Budget       : $0 (no approved budget)\n"
            "Grade        : UNKNOWN"
        )

    grade = get_employee_grade(employee)
    demo  = " [DEMO MAPPING]" if employee.get("_demo_mapping") else ""

    return (
        f"Employee ID  : {employee.get('employee_id', 'N/A')}{demo}\n"
        f"Name         : {employee.get('name', 'Unknown')}\n"
        f"Role         : {employee.get('role', 'Unknown')}\n"
        f"Grade        : {grade}\n"
        f"Department   : {employee.get('department', 'Unknown')}\n"
        f"Location     : {employee.get('location', 'Unknown')}\n"
        f"Tenure       : {employee.get('tenure_years', 0)} year(s)\n"
        f"Budget       : ${employee.get('budget_usd', 0):,}\n"
        f"Manager ID   : {employee.get('manager_id', 'N/A')}"
    )
