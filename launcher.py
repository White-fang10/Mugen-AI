"""
launcher.py
────────────────────────────────────────────────────────────────────────
MUGEN AI — Windows GUI Launcher
• Branded dark-mode tkinter interface with the Mugen AI logo
• Setup tab  : read/write .env API keys
• Control tab: Start/Stop Telegram Bot & Admin Panel
• Logs tab   : Live-streaming output from both services
• Status bar : Coloured service health indicators
────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import re
import sys
import queue
import signal
import subprocess
import threading
import webbrowser
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont

# ──────────────────────────────────────────────────────────────────────────────
# Resolve project root (works both as .py and inside frozen .exe)
# ──────────────────────────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).parent
else:
    ROOT = Path(__file__).parent


# ──────────────────────────────────────────────────────────────────────────────
# Design Tokens
# ──────────────────────────────────────────────────────────────────────────────
BG_DARK      = "#0d0d1a"
BG_CARD      = "#13132b"
BG_INPUT     = "#1a1a35"
BG_HOVER     = "#1f1f40"
ACCENT_BLUE  = "#4a9eff"
ACCENT_CYAN  = "#00d4ff"
ACCENT_PURP  = "#8b5cf6"
ACCENT_GRAD1 = "#3b82f6"
ACCENT_GRAD2 = "#8b5cf6"
TEXT_PRIMARY  = "#f0f0ff"
TEXT_MUTED    = "#8888aa"
TEXT_DIM      = "#555577"
SUCCESS      = "#22c55e"
WARNING      = "#f59e0b"
ERROR        = "#ef4444"
BORDER       = "#2a2a4a"
LOG_BOT_CLR  = "#60a5fa"
LOG_ADM_CLR  = "#a78bfa"

FONT_FAMILY  = "Segoe UI"
FONT_MONO    = "Consolas"


# ──────────────────────────────────────────────────────────────────────────────
# Helpers — .env
# ──────────────────────────────────────────────────────────────────────────────

def read_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.split("#")[0].strip()
    return result


def write_env(path: Path, values: dict[str, str]) -> None:
    existing: dict[str, str] = {}
    lines: list[str] = []
    if path.exists():
        raw = path.read_text(encoding="utf-8").splitlines()
        for line in raw:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                lines.append(line)
                continue
            if "=" in stripped:
                k, _, v = stripped.partition("=")
                existing[k.strip()] = line
                lines.append(line)
            else:
                lines.append(line)
    else:
        # Read from .env.example if available
        example = path.parent / ".env.example"
        if example.exists():
            lines = example.read_text(encoding="utf-8").splitlines()
            for line in lines:
                stripped = line.strip()
                if "=" in stripped and not stripped.startswith("#"):
                    k, _, _ = stripped.partition("=")
                    existing[k.strip()] = line

    # Update/append each value
    for key, val in values.items():
        found = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#") or "=" not in stripped:
                continue
            k, _, _ = stripped.partition("=")
            if k.strip() == key:
                lines[i] = f"{key}={val}"
                found = True
                break
        if not found:
            lines.append(f"{key}={val}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ──────────────────────────────────────────────────────────────────────────────
# Subprocess manager
# ──────────────────────────────────────────────────────────────────────────────

class ServiceProcess:
    """Wraps a subprocess and streams its stdout/stderr to a queue."""

    def __init__(self, name: str, cmd: list[str], cwd: Path, log_queue: queue.Queue):
        self.name = name
        self.cmd = cmd
        self.cwd = cwd
        self.log_queue = log_queue
        self._proc: subprocess.Popen | None = None
        self._threads: list[threading.Thread] = []

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> None:
        if self.running:
            return
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        self._proc = subprocess.Popen(
            self.cmd,
            cwd=str(self.cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        t = threading.Thread(target=self._stream, daemon=True)
        t.start()
        self._threads.append(t)

    def stop(self) -> None:
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None

    def _stream(self) -> None:
        if not self._proc or not self._proc.stdout:
            return
        for line in self._proc.stdout:
            self.log_queue.put((self.name, line.rstrip()))
        self.log_queue.put((self.name, f"[{self.name} process ended]"))


# ──────────────────────────────────────────────────────────────────────────────
# Main Application Window
# ──────────────────────────────────────────────────────────────────────────────

class MugenLauncher(tk.Tk):

    def __init__(self):
        super().__init__()

        # ── Window setup ──────────────────────────────────────────────────────
        self.title("Mugen AI — Launcher")
        self.geometry("940x680")
        self.minsize(800, 560)
        self.configure(bg=BG_DARK)
        self.resizable(True, True)

        # Load icon
        self._icon_img: tk.PhotoImage | None = None
        logo_path = ROOT / "mugen_logo.png"
        if logo_path.exists():
            try:
                self._icon_img = tk.PhotoImage(file=str(logo_path))
                self.iconphoto(True, self._icon_img)
            except Exception:
                pass

        # ── State ────────────────────────────────────────────────────────────
        self._log_queue: queue.Queue = queue.Queue()
        self._bot_svc: ServiceProcess | None = None
        self._adm_svc: ServiceProcess | None = None
        self._env_path = ROOT / ".env"
        self._env_data: dict[str, str] = {}

        # ── Build UI ─────────────────────────────────────────────────────────
        self._build_header()
        self._build_notebook()
        self._build_statusbar()

        # ── Bootstrap ────────────────────────────────────────────────────────
        self._load_env()
        self._start_log_poll()

        # Graceful close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        frame = tk.Frame(self, bg=BG_CARD, height=90)
        frame.pack(fill="x", side="top")
        frame.pack_propagate(False)

        # Logo
        logo_path = ROOT / "mugen_logo.png"
        if logo_path.exists():
            try:
                raw = tk.PhotoImage(file=str(logo_path))
                # Scale down
                scale = max(1, max(raw.width(), raw.height()) // 70)
                self._header_logo = raw.subsample(scale, scale)
                lbl = tk.Label(frame, image=self._header_logo,
                               bg=BG_CARD, cursor="hand2")
                lbl.pack(side="left", padx=(18, 10), pady=10)
            except Exception:
                pass

        # Title block
        title_frame = tk.Frame(frame, bg=BG_CARD)
        title_frame.pack(side="left", fill="y", pady=12)

        tk.Label(
            title_frame, text="MUGEN AI",
            font=(FONT_FAMILY, 20, "bold"),
            fg=ACCENT_CYAN, bg=BG_CARD,
        ).pack(anchor="w")

        tk.Label(
            title_frame, text="Autonomous Asset Request Bot  ·  Launcher",
            font=(FONT_FAMILY, 10),
            fg=TEXT_MUTED, bg=BG_CARD,
        ).pack(anchor="w")

        # Version badge
        badge = tk.Label(
            frame, text=" v2.0 ", font=(FONT_FAMILY, 9, "bold"),
            fg=BG_DARK, bg=ACCENT_PURP, padx=8, pady=2,
        )
        badge.pack(side="right", padx=18, pady=20)

        # Divider
        div = tk.Frame(self, bg=BORDER, height=1)
        div.pack(fill="x")

    # ── Notebook tabs ─────────────────────────────────────────────────────────

    def _build_notebook(self):
        style = ttk.Style(self)
        style.theme_use("default")

        style.configure("Dark.TNotebook",
                        background=BG_DARK, borderwidth=0, tabmargins=[0, 0, 0, 0])
        style.configure("Dark.TNotebook.Tab",
                        background=BG_CARD, foreground=TEXT_MUTED,
                        font=(FONT_FAMILY, 10), padding=[20, 10],
                        borderwidth=0)
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", BG_DARK)],
                  foreground=[("selected", ACCENT_CYAN)])

        self._nb = ttk.Notebook(self, style="Dark.TNotebook")
        self._nb.pack(fill="both", expand=True, padx=0, pady=0)

        self._tab_control = tk.Frame(self._nb, bg=BG_DARK)
        self._tab_setup   = tk.Frame(self._nb, bg=BG_DARK)
        self._tab_logs    = tk.Frame(self._nb, bg=BG_DARK)

        self._nb.add(self._tab_control, text="  ⚡  Control  ")
        self._nb.add(self._tab_setup,   text="  ⚙  Setup    ")
        self._nb.add(self._tab_logs,    text="  📋  Logs     ")

        self._build_control_tab()
        self._build_setup_tab()
        self._build_logs_tab()

    # ── Control tab ──────────────────────────────────────────────────────────

    def _build_control_tab(self):
        pad = dict(padx=30, pady=15)
        f = self._tab_control

        # ── Services grid ────────────────────────────────────────────────────
        services_frame = tk.Frame(f, bg=BG_DARK)
        services_frame.pack(fill="x", **pad)

        # Bot card
        self._bot_card = self._service_card(
            services_frame, "🤖  Telegram Bot",
            "Handles user conversations, asset requests, and security screening.",
            on_start=self._start_bot,
            on_stop=self._stop_bot,
        )
        self._bot_card.pack(fill="x", pady=(0, 12))

        # Admin card
        self._adm_card = self._service_card(
            services_frame, "🖥  Admin Panel",
            "Web dashboard at http://localhost:8080  ·  Manage requests, rules, API keys.",
            on_start=self._start_admin,
            on_stop=self._stop_admin,
            extra_btn=("🌐  Open in Browser", self._open_browser),
        )
        self._adm_card.pack(fill="x", pady=(0, 12))

        # ── Quick-action bar ─────────────────────────────────────────────────
        action_bar = tk.Frame(f, bg=BG_DARK)
        action_bar.pack(fill="x", padx=30, pady=(0, 10))

        self._btn_start_all = self._make_button(
            action_bar, "▶  Start All Services",
            bg=ACCENT_BLUE, command=self._start_all, width=22,
        )
        self._btn_start_all.pack(side="left", padx=(0, 12))

        self._btn_stop_all = self._make_button(
            action_bar, "⏹  Stop All Services",
            bg=ERROR, command=self._stop_all, width=22,
        )
        self._btn_stop_all.pack(side="left")

    def _service_card(self, parent, title, desc,
                      on_start, on_stop, extra_btn=None):
        card = tk.Frame(parent, bg=BG_CARD, relief="flat", bd=0)
        card.configure(highlightbackground=BORDER, highlightthickness=1)

        # Left: info
        info = tk.Frame(card, bg=BG_CARD)
        info.pack(side="left", fill="both", expand=True, padx=18, pady=14)

        title_row = tk.Frame(info, bg=BG_CARD)
        title_row.pack(fill="x")

        tk.Label(title_row, text=title, font=(FONT_FAMILY, 12, "bold"),
                 fg=TEXT_PRIMARY, bg=BG_CARD).pack(side="left")

        # Status dot (canvas circle)
        self._dot_canvas = tk.Canvas(title_row, width=14, height=14,
                                     bg=BG_CARD, highlightthickness=0)
        dot = self._make_dot(self._dot_canvas, "stopped")
        self._dot_canvas.pack(side="left", padx=(10, 0))

        # Store references on card frame for later access
        card._dot_canvas = self._dot_canvas
        card._dot_id = dot
        card._status_label = None

        status_lbl = tk.Label(title_row, text="Stopped",
                               font=(FONT_FAMILY, 9), fg=ERROR, bg=BG_CARD)
        status_lbl.pack(side="left", padx=(6, 0))
        card._status_label = status_lbl

        tk.Label(info, text=desc, font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD, wraplength=480, justify="left"
                 ).pack(fill="x", pady=(4, 0))

        # Right: buttons
        btns = tk.Frame(card, bg=BG_CARD)
        btns.pack(side="right", padx=18, pady=14)

        start_btn = self._make_button(btns, "▶  Start", bg=SUCCESS,
                                      command=on_start, width=12)
        start_btn.pack(pady=(0, 6))

        stop_btn = self._make_button(btns, "⏹  Stop", bg=ERROR,
                                     command=on_stop, width=12)
        stop_btn.pack(pady=(0, 6))

        if extra_btn:
            label, cmd = extra_btn
            self._make_button(btns, label, bg=ACCENT_PURP,
                              command=cmd, width=16).pack()

        card._start_btn = start_btn
        card._stop_btn  = stop_btn

        return card

    def _make_dot(self, canvas: tk.Canvas, state: str) -> int:
        color = SUCCESS if state == "running" else (WARNING if state == "starting" else ERROR)
        return canvas.create_oval(2, 2, 12, 12, fill=color, outline="")

    # ── Setup tab ────────────────────────────────────────────────────────────

    def _build_setup_tab(self):
        f = self._tab_setup
        canvas = tk.Canvas(f, bg=BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(f, orient="vertical", command=canvas.yview)
        self._setup_inner = tk.Frame(canvas, bg=BG_DARK)

        self._setup_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self._setup_inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._fields: dict[str, tk.StringVar] = {}
        self._setup_entries: dict[str, tk.Entry] = {}

        sections = [
            ("🔑  API Keys", [
                ("BOT_TOKEN",      "Telegram Bot Token",     "Get from @BotFather on Telegram", False),
                ("GROQ_API_KEY",   "Groq API Key",           "Get from console.groq.com",       True),
            ]),
            ("👤  Admin Configuration", [
                ("ADMIN_USER_IDS", "Admin Telegram User IDs", "Comma-separated numeric IDs",    False),
            ]),
            ("⚙  Optional Settings", [
                ("ADMIN_PORT",     "Admin Panel Port",        "Default: 8080",                  False),
                ("LOG_LEVEL",      "Log Level",               "DEBUG / INFO / WARNING / ERROR", False),
                ("CHROMA_PERSIST_DIR", "ChromaDB Directory", "Default: ./chroma_store",         False),
                ("DB_PATH",        "SQLite DB Path",          "Default: ./data/mugen.db",       False),
            ]),
        ]

        for section_title, fields in sections:
            self._setup_section(section_title, fields)

        # Save button
        btn_row = tk.Frame(self._setup_inner, bg=BG_DARK)
        btn_row.pack(fill="x", padx=30, pady=(10, 24))
        self._make_button(btn_row, "💾  Save Configuration",
                          bg=SUCCESS, command=self._save_env, width=24
                          ).pack(side="left")
        tk.Label(btn_row, text="Changes take effect on next service start",
                 fg=TEXT_DIM, bg=BG_DARK, font=(FONT_FAMILY, 9)
                 ).pack(side="left", padx=16)

    def _setup_section(self, title: str, fields: list):
        inner = self._setup_inner
        header = tk.Frame(inner, bg=BG_DARK)
        header.pack(fill="x", padx=30, pady=(20, 6))
        tk.Label(header, text=title, font=(FONT_FAMILY, 11, "bold"),
                 fg=ACCENT_CYAN, bg=BG_DARK).pack(side="left")
        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", padx=30, pady=(0, 6))

        for env_key, label, hint, secret in fields:
            row = tk.Frame(inner, bg=BG_DARK)
            row.pack(fill="x", padx=30, pady=4)

            lbl_col = tk.Frame(row, bg=BG_DARK, width=200)
            lbl_col.pack(side="left", fill="y")
            lbl_col.pack_propagate(False)
            tk.Label(lbl_col, text=label, font=(FONT_FAMILY, 10, "bold"),
                     fg=TEXT_PRIMARY, bg=BG_DARK).pack(anchor="w")
            tk.Label(lbl_col, text=hint, font=(FONT_FAMILY, 8),
                     fg=TEXT_DIM, bg=BG_DARK).pack(anchor="w")

            inp_col = tk.Frame(row, bg=BG_DARK)
            inp_col.pack(side="left", fill="x", expand=True, padx=(16, 0))

            var = tk.StringVar()
            self._fields[env_key] = var
            entry_kwargs = dict(
                textvariable=var,
                bg=BG_INPUT, fg=TEXT_PRIMARY,
                insertbackground=ACCENT_CYAN,
                relief="flat",
                font=(FONT_MONO, 10),
                bd=6,
            )
            if secret:
                entry_kwargs["show"] = "●"
            ent = tk.Entry(inp_col, **entry_kwargs)
            ent.pack(fill="x", ipady=6)
            ent.configure(highlightbackground=BORDER, highlightthickness=1,
                          highlightcolor=ACCENT_BLUE)
            self._setup_entries[env_key] = ent

            if secret:
                toggle_var = tk.BooleanVar(value=False)
                def make_toggle(e=ent, tv=toggle_var):
                    def _toggle():
                        e.configure(show="" if tv.get() else "●")
                    return _toggle
                tk.Checkbutton(
                    inp_col, text="Show", variable=toggle_var,
                    command=make_toggle(), bg=BG_DARK, fg=TEXT_MUTED,
                    activebackground=BG_DARK, activeforeground=TEXT_PRIMARY,
                    selectcolor=BG_INPUT, font=(FONT_FAMILY, 9),
                ).pack(anchor="w")

    # ── Logs tab ─────────────────────────────────────────────────────────────

    def _build_logs_tab(self):
        f = self._tab_logs

        # Toolbar
        toolbar = tk.Frame(f, bg=BG_CARD, height=40)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="Live Service Logs", font=(FONT_FAMILY, 10, "bold"),
                 fg=TEXT_PRIMARY, bg=BG_CARD).pack(side="left", padx=16, pady=8)

        self._make_button(toolbar, "🗑  Clear", bg=BG_HOVER,
                          command=self._clear_logs, width=10, fg=TEXT_MUTED
                          ).pack(side="right", padx=10, pady=6)

        # Legend
        legend = tk.Frame(toolbar, bg=BG_CARD)
        legend.pack(side="right", padx=10)
        tk.Label(legend, text="●", fg=LOG_BOT_CLR, bg=BG_CARD,
                 font=(FONT_FAMILY, 12)).pack(side="left")
        tk.Label(legend, text="Bot  ", fg=TEXT_MUTED, bg=BG_CARD,
                 font=(FONT_FAMILY, 9)).pack(side="left")
        tk.Label(legend, text="●", fg=LOG_ADM_CLR, bg=BG_CARD,
                 font=(FONT_FAMILY, 12)).pack(side="left")
        tk.Label(legend, text="Admin", fg=TEXT_MUTED, bg=BG_CARD,
                 font=(FONT_FAMILY, 9)).pack(side="left")

        tk.Frame(f, bg=BORDER, height=1).pack(fill="x")

        # Log text widget
        log_frame = tk.Frame(f, bg=BG_DARK)
        log_frame.pack(fill="both", expand=True, padx=0, pady=0)

        self._log_text = tk.Text(
            log_frame,
            bg="#0a0a14", fg=TEXT_PRIMARY,
            font=(FONT_MONO, 9),
            relief="flat", bd=0,
            wrap="word",
            state="disabled",
        )
        vsb = ttk.Scrollbar(log_frame, orient="vertical",
                             command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._log_text.pack(fill="both", expand=True, padx=2, pady=2)

        # Tag colours
        self._log_text.tag_configure("bot",       foreground=LOG_BOT_CLR)
        self._log_text.tag_configure("admin",      foreground=LOG_ADM_CLR)
        self._log_text.tag_configure("timestamp",  foreground=TEXT_DIM)
        self._log_text.tag_configure("system",     foreground=WARNING)

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=BG_CARD, height=30)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Frame(bar, bg=BORDER, height=1).pack(fill="x", side="top")

        self._bot_status_lbl = tk.Label(
            bar, text="🤖 Bot: Stopped",
            font=(FONT_FAMILY, 9), fg=ERROR, bg=BG_CARD,
        )
        self._bot_status_lbl.pack(side="left", padx=16, pady=4)

        sep = tk.Label(bar, text="|", fg=BORDER, bg=BG_CARD,
                       font=(FONT_FAMILY, 9))
        sep.pack(side="left")

        self._adm_status_lbl = tk.Label(
            bar, text="🖥 Admin: Stopped",
            font=(FONT_FAMILY, 9), fg=ERROR, bg=BG_CARD,
        )
        self._adm_status_lbl.pack(side="left", padx=16, pady=4)

        self._env_lbl = tk.Label(
            bar, text=f"📁 {self._env_path}",
            font=(FONT_FAMILY, 9), fg=TEXT_DIM, bg=BG_CARD,
        )
        self._env_lbl.pack(side="right", padx=16, pady=4)

    # ── Business logic ────────────────────────────────────────────────────────

    def _python_cmd(self) -> str:
        """Return path to python inside .venv if available."""
        candidates = [
            ROOT / ".venv" / "Scripts" / "python.exe",
            ROOT / "venv"  / "Scripts" / "python.exe",
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return sys.executable  # fall back to launcher's own Python

    def _load_env(self):
        self._env_data = read_env(self._env_path)
        for key, var in self._fields.items():
            var.set(self._env_data.get(key, ""))

    def _save_env(self):
        updates = {k: v.get().strip() for k, v in self._fields.items() if v.get().strip()}
        write_env(self._env_path, updates)
        self._env_data = read_env(self._env_path)
        self._log_system("✅  Configuration saved to .env")
        messagebox.showinfo("Saved", "Configuration saved!\nRestart services to apply changes.")

    def _start_bot(self):
        if self._bot_svc and self._bot_svc.running:
            return
        py = self._python_cmd()
        self._bot_svc = ServiceProcess(
            "Bot", [py, "-m", "bot.main"], ROOT, self._log_queue
        )
        self._bot_svc.start()
        self._log_system("🤖  Telegram Bot starting…")
        self._update_status()

    def _stop_bot(self):
        if self._bot_svc:
            self._bot_svc.stop()
            self._log_system("⏹  Telegram Bot stopped.")
        self._update_status()

    def _start_admin(self):
        if self._adm_svc and self._adm_svc.running:
            return
        py = self._python_cmd()
        self._adm_svc = ServiceProcess(
            "Admin", [py, "-m", "admin_panel.run"], ROOT, self._log_queue
        )
        self._adm_svc.start()
        self._log_system("🖥  Admin Panel starting at http://localhost:8080…")
        self._update_status()

    def _stop_admin(self):
        if self._adm_svc:
            self._adm_svc.stop()
            self._log_system("⏹  Admin Panel stopped.")
        self._update_status()

    def _start_all(self):
        self._start_bot()
        self._start_admin()

    def _stop_all(self):
        self._stop_bot()
        self._stop_admin()

    def _open_browser(self):
        port = self._env_data.get("ADMIN_PORT", "8080")
        webbrowser.open(f"http://localhost:{port}")

    # ── Status helpers ────────────────────────────────────────────────────────

    def _update_status(self):
        bot_running = self._bot_svc is not None and self._bot_svc.running
        adm_running = self._adm_svc is not None and self._adm_svc.running

        # Status bar
        self._bot_status_lbl.configure(
            text="🤖 Bot: Running" if bot_running else "🤖 Bot: Stopped",
            fg=SUCCESS if bot_running else ERROR,
        )
        self._adm_status_lbl.configure(
            text="🖥 Admin: Running" if adm_running else "🖥 Admin: Stopped",
            fg=SUCCESS if adm_running else ERROR,
        )

        # Cards
        self._update_card(self._bot_card, bot_running)
        self._update_card(self._adm_card, adm_running)

    def _update_card(self, card: tk.Frame, running: bool):
        color = SUCCESS if running else ERROR
        text  = "Running" if running else "Stopped"
        card._dot_canvas.itemconfigure(card._dot_id, fill=color)
        card._status_label.configure(text=text, fg=color)

    # ── Log helpers ───────────────────────────────────────────────────────────

    def _start_log_poll(self):
        self._poll_logs()

    def _poll_logs(self):
        try:
            while True:
                name, line = self._log_queue.get_nowait()
                self._append_log(name, line)
        except queue.Empty:
            pass
        self._update_status()
        self.after(150, self._poll_logs)

    def _append_log(self, source: str, text: str):
        self._log_text.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        tag = "bot" if source == "Bot" else "admin"
        self._log_text.insert("end", f"[{ts}] ", "timestamp")
        self._log_text.insert("end", f"[{source}] ", tag)
        self._log_text.insert("end", text + "\n")
        self._log_text.configure(state="disabled")
        self._log_text.see("end")

    def _log_system(self, msg: str):
        self._log_text.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_text.insert("end", f"[{ts}] ", "timestamp")
        self._log_text.insert("end", msg + "\n", "system")
        self._log_text.configure(state="disabled")
        self._log_text.see("end")

    def _clear_logs(self):
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.configure(state="disabled")

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _make_button(self, parent, text, bg=ACCENT_BLUE, command=None,
                     width=None, fg=BG_DARK):
        btn = tk.Button(
            parent, text=text, command=command,
            bg=bg, fg=fg,
            activebackground=bg, activeforeground=fg,
            relief="flat", bd=0,
            font=(FONT_FAMILY, 9, "bold"),
            cursor="hand2",
            padx=12, pady=6,
            width=width,
        )
        btn.bind("<Enter>", lambda e: btn.configure(bg=self._lighten(bg)))
        btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
        return btn

    @staticmethod
    def _lighten(hex_color: str, amount: int = 20) -> str:
        try:
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            r = min(255, r + amount)
            g = min(255, g + amount)
            b = min(255, b + amount)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color

    def _on_close(self):
        if (self._bot_svc and self._bot_svc.running) or \
           (self._adm_svc and self._adm_svc.running):
            if not messagebox.askyesno(
                "Services Running",
                "Services are still running.\nStop them and exit?",
            ):
                return
        self._stop_all()
        self.destroy()


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    # Load .env into environment before anything else
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.split("#")[0].strip()
            if k and k not in os.environ:
                os.environ[k] = v

    app = MugenLauncher()
    app.mainloop()


if __name__ == "__main__":
    main()
