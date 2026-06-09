"""
admin_panel/api.py
─────────────────────────────────────────────────────────────────────────────
MUGEN AI — Company Admin REST API
══════════════════════════════════════════════════════════════════════════════
Endpoints:
  GET  /                        → Serve admin dashboard HTML
  GET  /api/status              → Health check + indexed rulebook list
  POST /api/upload-rulebook     → Upload PDF → trigger RAG ingest
  GET  /api/hris                → Return current hris.json
  POST /api/hris/upload         → Replace hris.json with an uploaded JSON file
  POST /api/hris/employee       → Add a single employee
  DELETE /api/hris/{employee_id}→ Remove employee by ID
  GET  /api/config/keys         → Return masked API keys from .env
  POST /api/config/keys         → Update BOT_TOKEN / GROQ_API_KEY in .env
"""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import structlog
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Path resolution ──────────────────────────────────────────────────────────
# admin_panel/api.py lives one level below the project root
PROJECT_ROOT  = Path(__file__).parent.parent
DATA_DIR      = PROJECT_ROOT / "data"
HRIS_PATH     = DATA_DIR / "hris.json"
RULEBOOKS_DIR = PROJECT_ROOT / "rulebooks"
STATIC_DIR    = Path(__file__).parent / "static"

log = structlog.get_logger(__name__)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="MUGEN AI Admin Panel",
    description="Company admin interface for rulebook and HRIS management",
    version="1.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ─────────────────────────────────────────────────────────────────────────────
# Root → serve dashboard
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def serve_dashboard():
    return FileResponse(str(STATIC_DIR / "index.html"))


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/status
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/status")
async def api_status():
    """Health check + list of indexed rulebook PDFs."""
    rulebook_files = sorted(
        [f.name for f in RULEBOOKS_DIR.glob("*.pdf")]
    ) if RULEBOOKS_DIR.exists() else []

    # Try to get chroma indexed sources
    indexed_sources: List[str] = []
    try:
        from bot.rag.retriever import get_indexed_sources
        indexed_sources = get_indexed_sources()
    except Exception:
        pass

    return {
        "status": "ok",
        "rulebook_files_on_disk": rulebook_files,
        "chroma_indexed_sources": indexed_sources,
        "hris_path": str(HRIS_PATH),
        "hris_exists": HRIS_PATH.exists(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/upload-rulebook
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/upload-rulebook")
async def upload_rulebook(file: UploadFile = File(...)):
    """
    Upload a PDF policy rulebook and ingest it into ChromaDB.
    Returns the ingestion report.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    RULEBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    dest = RULEBOOKS_DIR / file.filename

    # Save the uploaded file
    async with aiofiles.open(dest, "wb") as out:
        content = await file.read()
        await out.write(content)

    log.info("rulebook_uploaded_via_panel", file=file.filename, size=len(content))

    # Run RAG ingestion
    try:
        from bot.rag.pdf_loader import ingest_pdf
        report = await ingest_pdf(pdf_path=dest, admin_id=0)
        return {
            "success": True,
            "file": file.filename,
            "chunks_created": report.chunks_created,
            "was_duplicate": report.was_duplicate,
            "pages_processed": report.pages_total,
        }
    except Exception as exc:
        log.error("rulebook_ingest_error", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/hris
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/hris")
async def get_hris():
    """Return the full contents of hris.json."""
    if not HRIS_PATH.exists():
        return {"employees": []}
    async with aiofiles.open(HRIS_PATH, "r", encoding="utf-8") as f:
        data = json.loads(await f.read())
    return data


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/hris/upload  — replace entire hris.json with uploaded file
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/hris/upload")
async def upload_hris(file: UploadFile = File(...)):
    """Replace hris.json with a new uploaded JSON file."""
    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files are accepted.")

    content = await file.read()
    try:
        data = json.loads(content)
        if "employees" not in data or not isinstance(data["employees"], list):
            raise ValueError("JSON must have an 'employees' array at the root.")
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid HRIS JSON: {exc}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Backup existing
    if HRIS_PATH.exists():
        shutil.copy(HRIS_PATH, HRIS_PATH.with_suffix(".json.bak"))

    async with aiofiles.open(HRIS_PATH, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=2))

    log.info("hris_replaced_via_panel", employees=len(data["employees"]))
    return {"success": True, "employees_count": len(data["employees"])}


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/hris/employee  — add a single employee
# ─────────────────────────────────────────────────────────────────────────────

class Employee(BaseModel):
    employee_id: str
    name: str
    role: str
    department: str
    tenure_years: int
    budget_usd: int
    manager_id: Optional[str] = None
    location: Optional[str] = "Remote"


@app.post("/api/hris/employee")
async def add_employee(employee: Employee):
    """Add a single employee record to hris.json."""
    if HRIS_PATH.exists():
        async with aiofiles.open(HRIS_PATH, "r", encoding="utf-8") as f:
            data = json.loads(await f.read())
    else:
        data = {"employees": []}

    # Check for duplicate ID
    existing_ids = {e.get("employee_id") for e in data["employees"]}
    if employee.employee_id in existing_ids:
        raise HTTPException(
            status_code=409,
            detail=f"Employee ID '{employee.employee_id}' already exists."
        )

    data["employees"].append(employee.model_dump())
    async with aiofiles.open(HRIS_PATH, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=2))

    log.info("employee_added_via_panel", employee_id=employee.employee_id)
    return {"success": True, "employee_id": employee.employee_id}


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/hris/{employee_id}  — remove employee
# ─────────────────────────────────────────────────────────────────────────────

@app.delete("/api/hris/{employee_id}")
async def delete_employee(employee_id: str):
    """Remove an employee from hris.json by their employee_id."""
    if not HRIS_PATH.exists():
        raise HTTPException(status_code=404, detail="HRIS data not found.")

    async with aiofiles.open(HRIS_PATH, "r", encoding="utf-8") as f:
        data = json.loads(await f.read())

    original_count = len(data["employees"])
    data["employees"] = [
        e for e in data["employees"] if e.get("employee_id") != employee_id
    ]

    if len(data["employees"]) == original_count:
        raise HTTPException(
            status_code=404,
            detail=f"Employee '{employee_id}' not found."
        )

    async with aiofiles.open(HRIS_PATH, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=2))

    log.info("employee_deleted_via_panel", employee_id=employee_id)
    return {"success": True, "deleted_employee_id": employee_id}


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/config/keys  — return masked keys
# POST /api/config/keys — update BOT_TOKEN / GROQ_API_KEY in .env
# ─────────────────────────────────────────────────────────────────────────────

ENV_PATH = PROJECT_ROOT / ".env"


def _mask(value: str) -> str:
    """Show first 6 + last 4 chars, mask the middle."""
    if not value or len(value) < 12:
        return "*" * max(len(value), 8)
    return value[:6] + "*" * (len(value) - 10) + value[-4:]


def _read_env_file() -> dict:
    """Parse the .env file into a dict of key→value strings."""
    env: dict = {}
    if not ENV_PATH.exists():
        return env
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        # Strip inline comments
        val = val.split("#")[0].strip()
        env[key.strip()] = val
    return env


def _write_env_file(updates: dict) -> None:
    """Update specific keys in the .env file, preserving all other content."""
    if not ENV_PATH.exists():
        lines = []
    else:
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines(keepends=True)

    remaining = dict(updates)  # keys still to be written
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                new_lines.append(f"{key}={remaining.pop(key)}\n")
                continue
        new_lines.append(line if line.endswith("\n") else line + "\n")

    # Append any brand-new keys not previously in the file
    for key, val in remaining.items():
        new_lines.append(f"{key}={val}\n")

    ENV_PATH.write_text("".join(new_lines), encoding="utf-8")


@app.get("/api/config/keys")
async def get_config_keys():
    """Return masked BOT_TOKEN and GROQ_API_KEY from the .env file."""
    env = _read_env_file()
    bot_token  = env.get("BOT_TOKEN", "")
    groq_key   = env.get("GROQ_API_KEY", "")
    return {
        "bot_token_set":   bool(bot_token),
        "groq_key_set":    bool(groq_key),
        "bot_token_masked":  _mask(bot_token)  if bot_token  else "",
        "groq_key_masked":   _mask(groq_key)   if groq_key   else "",
    }


class KeysUpdate(BaseModel):
    bot_token:    Optional[str] = None
    groq_api_key: Optional[str] = None


@app.post("/api/config/keys")
async def update_config_keys(payload: KeysUpdate):
    """Update BOT_TOKEN and/or GROQ_API_KEY in the .env file."""
    updates: Dict[str, str] = {}
    if payload.bot_token and payload.bot_token.strip():
        updates["BOT_TOKEN"] = payload.bot_token.strip()
    if payload.groq_api_key and payload.groq_api_key.strip():
        updates["GROQ_API_KEY"] = payload.groq_api_key.strip()

    if not updates:
        raise HTTPException(status_code=400, detail="No keys provided to update.")

    _write_env_file(updates)
    log.info("api_keys_updated_via_panel", keys=list(updates.keys()))
    return {"success": True, "updated": list(updates.keys())}
