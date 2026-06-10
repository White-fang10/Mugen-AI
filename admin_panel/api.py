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
import os
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import structlog
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import aiosqlite

# ── Path resolution ──────────────────────────────────────────────────────────
# admin_panel/api.py lives one level below the project root
PROJECT_ROOT  = Path(__file__).parent.parent
DATA_DIR      = PROJECT_ROOT / "data"
HRIS_PATH     = DATA_DIR / "hris.json"
RULEBOOKS_DIR = PROJECT_ROOT / "rulebooks"
STATIC_DIR    = Path(__file__).parent / "static"

log = structlog.get_logger(__name__)


# ── Self-ping keepalive (prevents Render free-tier sleep) ─────────────────────

async def _keepalive_loop() -> None:
    """
    Pings the service's own /api/ping endpoint every 14 minutes.
    Render free tier spins down after 15 min of inactivity — this keeps
    both the Admin Panel and the Telegram Bot alive 24/7.
    """
    await asyncio.sleep(60)  # wait 1 min after startup before first ping
    service_url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if not service_url:
        # Try to build the URL from RENDER_SERVICE_NAME
        svc_name = os.environ.get("RENDER_SERVICE_NAME", "")
        if svc_name:
            service_url = f"https://{svc_name}.onrender.com"
    if not service_url:
        log.warning("keepalive_disabled", reason="RENDER_EXTERNAL_URL not set")
        return

    ping_url = service_url.rstrip("/") + "/api/ping"
    log.info("keepalive_started", url=ping_url)

    try:
        import httpx
    except ImportError:
        log.warning("keepalive_disabled", reason="httpx not installed")
        return

    while True:
        await asyncio.sleep(14 * 60)  # 14 minutes
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(ping_url)
                log.info("keepalive_ping", status=resp.status_code)
        except Exception as exc:
            log.warning("keepalive_ping_failed", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: start keepalive task on boot."""
    task = asyncio.create_task(_keepalive_loop())
    log.info("keepalive_task_started")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="MUGEN AI Admin Panel",
    description="Company admin interface for rulebook and HRIS management",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── /api/ping ─────────────────────────────────────────────────────────────────

@app.get("/api/ping")
async def ping():
    """Ultra-lightweight keepalive endpoint."""
    return {"pong": True}


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

    # Try to get chroma indexed sources — with a hard timeout so we never
    # block the status response (ChromaDB cold-start can take 30+ seconds).
    indexed_sources: List[str] = []
    try:
        def _get_sources() -> List[str]:
            from bot.rag.retriever import get_indexed_sources
            return get_indexed_sources()

        loop = asyncio.get_event_loop()
        indexed_sources = await asyncio.wait_for(
            loop.run_in_executor(None, _get_sources),
            timeout=3.0,  # max 3 s — return empty list if slower
        )
    except Exception:
        pass  # ChromaDB not ready yet or timed out — that's fine

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
    """Return the full contents of hris.json, normalising legacy field names.

    Handles both old-format keys (id / budget) and canonical keys
    (employee_id / budget_usd) so the dashboard renders correctly regardless
    of which format the file was originally created with.
    """
    if not HRIS_PATH.exists():
        return {"employees": []}
    async with aiofiles.open(HRIS_PATH, "r", encoding="utf-8") as f:
        data = json.loads(await f.read())

    # Normalise field aliases so the dashboard always gets canonical names
    _field_aliases: Dict[str, str] = {
        "id":     "employee_id",
        "emp_id": "employee_id",
        "budget": "budget_usd",
    }
    normalised: List[Dict] = []
    for emp in data.get("employees", []):
        norm: Dict[str, Any] = {}
        for k, v in emp.items():
            canonical = _field_aliases.get(k, k)
            # Keep the canonical key; do NOT overwrite if already present
            if canonical not in norm:
                norm[canonical] = v
        normalised.append(norm)

    data["employees"] = normalised
    return data


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/hris/upload  — replace entire hris.json with uploaded file
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/hris/upload")
async def upload_hris(file: UploadFile = File(...)):
    """Replace hris.json with a new uploaded JSON file.
    Normalises common alternate field names so uploads don't break the dashboard:
      id        → employee_id
      budget    → budget_usd
      emp_id    → employee_id
    """
    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files are accepted.")

    content = await file.read()
    try:
        data = json.loads(content)
        if "employees" not in data or not isinstance(data["employees"], list):
            raise ValueError("JSON must have an 'employees' array at the root.")
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid HRIS JSON: {exc}")

    # ── Normalise field names ─────────────────────────────────────────────────
    _field_aliases: Dict[str, str] = {
        "id":       "employee_id",
        "emp_id":   "employee_id",
        "budget":   "budget_usd",
    }
    normalised: List[Dict] = []
    for emp in data["employees"]:
        norm: Dict[str, Any] = {}
        for k, v in emp.items():
            canonical = _field_aliases.get(k, k)   # rename if alias, else keep
            norm[canonical] = v
        # Ensure required numeric fields are int, not None / string
        for num_field in ("budget_usd", "tenure_years"):
            raw = norm.get(num_field)
            if raw is None or raw == "":
                norm[num_field] = 0
            else:
                try:
                    norm[num_field] = int(float(str(raw)))
                except (ValueError, TypeError):
                    norm[num_field] = 0
        normalised.append(norm)

    data["employees"] = normalised

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Backup existing
    if HRIS_PATH.exists():
        shutil.copy(HRIS_PATH, HRIS_PATH.with_suffix(".json.bak"))

    async with aiofiles.open(HRIS_PATH, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=2))

    log.info("hris_replaced_via_panel", employees=len(normalised))
    return {"success": True, "employees_count": len(normalised)}


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
# GET /api/requests  — fetch all asset requests from SQLite
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/requests")
async def get_all_requests(
    status: Optional[str] = None,
    limit: int = 100,
):
    """
    Return asset requests from the SQLite DB.
    Optional ?status=APPROVED|REJECTED|FLAGGED|PENDING filter.
    """
    try:
        from bot.config import get_settings
        settings = get_settings()
        db_path  = str(settings.db_path)

        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            # Try to include user_identity; fall back gracefully if column absent
            _cols = """id, user_id, asset_name, asset_category,
                       justification, urgency, cost_estimate,
                       status, decision_reason, suggested_alternative,
                       employee_grade, rag_signal, policy_refs,
                       created_at, updated_at"""
            _cols_with_identity = _cols + ", user_identity"

            # Detect whether user_identity column exists
            try:
                await db.execute("SELECT user_identity FROM asset_requests LIMIT 1")
                select_cols = _cols_with_identity
            except Exception:
                select_cols = _cols

            if status:
                cur = await db.execute(
                    f"""SELECT {select_cols}
                       FROM asset_requests
                       WHERE UPPER(status)=?
                       ORDER BY created_at DESC LIMIT ?""",
                    (status.upper(), limit),
                )
            else:
                cur = await db.execute(
                    f"""SELECT {select_cols}
                       FROM asset_requests
                       ORDER BY created_at DESC LIMIT ?""",
                    (limit,),
                )
            rows = await cur.fetchall()
            requests = []
            for r in rows:
                row = dict(r)
                # Parse policy_refs JSON string → list
                try:
                    row["policy_refs"] = json.loads(row.get("policy_refs") or "[]")
                except Exception:
                    row["policy_refs"] = []
                requests.append(row)

        # Summary counts
        counts: Dict[str, int] = {}
        for r in requests:
            s = r.get("status", "UNKNOWN")
            counts[s] = counts.get(s, 0) + 1

        return {"requests": requests, "counts": counts, "total": len(requests)}
    except Exception as exc:
        log.error("requests_fetch_error", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Could not read requests DB: {exc}")


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
