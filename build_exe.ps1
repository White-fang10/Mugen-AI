# ==============================================================================
#  MUGEN AI — EXE Build Script
#  Produces:  dist\MugenAI.exe
#
#  Usage:
#    .\build_exe.ps1
#
#  Requirements:
#    • Python 3.10+ with pip
#    • Virtual environment (.venv) recommended
# ==============================================================================

param (
    [switch]$SkipDeps,   # Skip pip install step
    [switch]$Clean       # Delete build\ and dist\ before building
)

# ── Helpers ────────────────────────────────────────────────────────────────────

function Write-Banner {
    Clear-Host
    Write-Host ""
    Write-Host "  ╔══════════════════════════════════════════════════════════╗" -ForegroundColor DarkMagenta
    Write-Host "  ║         MUGEN AI  —  EXE Build System  v2.0             ║" -ForegroundColor Magenta
    Write-Host "  ║         Packaging Telegram Bot + Admin Panel             ║" -ForegroundColor DarkMagenta
    Write-Host "  ╚══════════════════════════════════════════════════════════╝" -ForegroundColor DarkMagenta
    Write-Host ""
}

function Write-Step([string]$n, [string]$msg) {
    Write-Host "  [$n] $msg" -ForegroundColor Cyan
}

function Write-OK([string]$msg)   { Write-Host "     ✔  $msg" -ForegroundColor Green }
function Write-Warn([string]$msg) { Write-Host "     ⚠  $msg" -ForegroundColor Yellow }
function Write-Fail([string]$msg) { Write-Host "     ✖  $msg" -ForegroundColor Red }
function Write-Sep                { Write-Host "  ──────────────────────────────────────────────────────────" -ForegroundColor DarkGray }

# ── Locate project root ────────────────────────────────────────────────────────

$Root = $PSScriptRoot
Set-Location $Root
Write-Banner

# ── Resolve Python ────────────────────────────────────────────────────────────
Write-Step "1/6" "Locating Python interpreter..."

$python = $null
$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
    Write-OK "Using venv Python: $python"
} else {
    foreach ($c in @("python", "python3", "py")) {
        try {
            $ver = & $c --version 2>&1
            if ($ver -match "Python (\d+\.\d+)") {
                $python = $c
                Write-OK "Found $ver  (command: $c)"
                break
            }
        } catch {}
    }
}

if (-not $python) {
    Write-Fail "Python not found. Install Python 3.10+ from https://python.org"
    exit 1
}

Write-Sep

# ── Install build dependencies ────────────────────────────────────────────────
Write-Step "2/6" "Installing build dependencies..."

if (-not $SkipDeps) {
    Write-Warn "Installing Pillow (for icon conversion)..."
    & $python -m pip install pillow --quiet
    if ($LASTEXITCODE -ne 0) { Write-Fail "Failed to install Pillow"; exit 1 }

    Write-Warn "Installing PyInstaller..."
    & $python -m pip install pyinstaller --quiet
    if ($LASTEXITCODE -ne 0) { Write-Fail "Failed to install PyInstaller"; exit 1 }

    Write-OK "Build dependencies ready."
} else {
    Write-Warn "-SkipDeps flag set — assuming PyInstaller + Pillow are installed."
}

Write-Sep

# ── Generate ICO from PNG ─────────────────────────────────────────────────────
Write-Step "3/6" "Converting Mugen AI logo PNG → ICO..."

$logoSrc = Join-Path $Root "mugen_logo.png"
$logoDst = Join-Path $Root "mugen_logo.ico"

if (-not (Test-Path $logoSrc)) {
    Write-Fail "mugen_logo.png not found in $Root"
    exit 1
}

& $python (Join-Path $Root "make_icon.py")
if ($LASTEXITCODE -ne 0) { Write-Fail "Icon conversion failed"; exit 1 }
Write-OK "Icon ready: mugen_logo.ico"

Write-Sep

# ── Optional clean ────────────────────────────────────────────────────────────
Write-Step "4/6" "Preparing build directories..."

if ($Clean) {
    Write-Warn "Cleaning previous build artifacts..."
    @("build", "dist") | ForEach-Object {
        $p = Join-Path $Root $_
        if (Test-Path $p) {
            Remove-Item $p -Recurse -Force
            Write-OK "Removed: $_\"
        }
    }
}

Write-OK "Build directories ready."
Write-Sep

# ── Run PyInstaller ───────────────────────────────────────────────────────────
Write-Step "5/6" "Running PyInstaller (this may take 5-15 minutes)..."
Write-Host ""
Write-Warn "Bundling Python runtime + all dependencies..."
Write-Warn "Please be patient — ML libraries take a while..."
Write-Host ""

& $python -m PyInstaller MugenAI.spec --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Fail "PyInstaller failed. Check the output above for errors."
    exit 1
}

Write-Sep

# ── Verify output ─────────────────────────────────────────────────────────────
Write-Step "6/6" "Verifying output..."

$exePath = Join-Path $Root "dist\MugenAI.exe"

if (Test-Path $exePath) {
    $sizeMB = [Math]::Round((Get-Item $exePath).Length / 1MB, 1)
    Write-Host ""
    Write-Host "  ╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "  ║                  BUILD SUCCESSFUL! 🎉                   ║" -ForegroundColor Green
    Write-Host "  ╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-OK "Output : dist\MugenAI.exe"
    Write-OK "Size   : ${sizeMB} MB"
    Write-Host ""
    Write-Host "  Distribution Notes:" -ForegroundColor DarkGray
    Write-Host "  • Copy dist\MugenAI.exe to any Windows PC — no Python needed!" -ForegroundColor Gray
    Write-Host "  • First launch: configure BOT_TOKEN + GROQ_API_KEY in the Setup tab" -ForegroundColor Gray
    Write-Host "  • The .env file will be created next to MugenAI.exe" -ForegroundColor Gray
    Write-Host ""

    $open = Read-Host "  Open dist\ folder now? [Y/n]"
    if ($open -notmatch "^[Nn]") {
        Start-Process explorer (Join-Path $Root "dist")
    }
} else {
    Write-Fail "MugenAI.exe not found in dist\. Build may have failed silently."
    exit 1
}
