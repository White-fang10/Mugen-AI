# MugenAI.spec
# ─────────────────────────────────────────────────────────────────────────────
# PyInstaller spec for MUGEN AI — builds a single MugenAI.exe
#
# Usage:
#   pyinstaller MugenAI.spec
#
# Output:  dist\MugenAI.exe
# ─────────────────────────────────────────────────────────────────────────────

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None

# ── Collect package data + submodules ─────────────────────────────────────────

datas = []
binaries = []
hiddenimports = []

# chromadb – heavy; needs full collection
for pkg in ["chromadb"]:
    d, b, h = collect_all(pkg)
    datas     += d
    binaries  += b
    hiddenimports += h

# sentence-transformers
for pkg in ["sentence_transformers", "tokenizers", "transformers"]:
    d, b, h = collect_all(pkg)
    datas     += d
    binaries  += b
    hiddenimports += h

# langchain ecosystem
for pkg in [
    "langchain", "langchain_core", "langchain_groq",
    "langchain_community", "langchain_text_splitters",
]:
    d, b, h = collect_all(pkg)
    datas     += d
    binaries  += b
    hiddenimports += h

# fastapi / uvicorn
for pkg in ["fastapi", "uvicorn", "starlette"]:
    d, b, h = collect_all(pkg)
    datas     += d
    binaries  += b
    hiddenimports += h

# python-telegram-bot
d, b, h = collect_all("telegram")
datas     += d
binaries  += b
hiddenimports += h

# groq SDK
d, b, h = collect_all("groq")
datas     += d
binaries  += b
hiddenimports += h

# Additional hidden imports
hiddenimports += [
    "aiosqlite",
    "structlog",
    "pydantic",
    "pydantic_settings",
    "dotenv",
    "ujson",
    "tenacity",
    "httpx",
    "anyio",
    "anyio._backends._asyncio",
    "anyio._backends._trio",
    "asyncio",
    "tkinter",
    "tkinter.ttk",
    "tkinter.messagebox",
    "tkinter.font",
    "PIL",
    "PIL.Image",
    "PIL.ImageTk",
    "aiofiles",
    "multipart",
    "email.mime.text",
    "email.mime.multipart",
    "pydantic.deprecated.class_validators",
    "pkg_resources.py2_warn",
]

# ── Project data files ────────────────────────────────────────────────────────

project_datas = [
    # Admin panel static files
    ("admin_panel/static", "admin_panel/static"),
    # Environment example
    (".env.example", "."),
    # Logo
    ("mugen_logo.png", "."),
    ("mugen_logo.ico", "."),
    # Empty placeholder dirs (PyInstaller won't include empty dirs,
    # so we create placeholder files in them at runtime via the launcher)
]

# Add data dirs only if they exist and have content
import os

for src, dst in [
    ("rulebooks", "rulebooks"),
    ("data", "data"),
]:
    if os.path.exists(src) and any(os.scandir(src)):
        project_datas.append((src, dst))

datas += project_datas

# ── Analysis ──────────────────────────────────────────────────────────────────

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "numpy.distutils",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
        "sphinx",
        "docutils",
        "_tkinter",   # already linked via tkinter hook
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="MugenAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,          # compress – reduces size ~30 %
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,     # no black terminal window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="mugen_logo.ico",
    version_file=None,
)
