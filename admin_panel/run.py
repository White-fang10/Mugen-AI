"""
admin_panel/run.py
─────────────────────────────────────────────────────────────────────────────
Entry point for the MUGEN AI Admin Panel.
Run with:  python -m admin_panel.run
Serves at: http://localhost:8080
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "admin_panel.api:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        reload_dirs=["admin_panel"],
    )
