# ==============================================================================
#  MUGEN AI -- PowerShell Startup Script
#  Launches: Telegram Bot  +  Admin Panel (http://localhost:8080)
# ==============================================================================
#
# Usage:
#   .\Start-Mugen.ps1              # Start both services (default)
#   .\Start-Mugen.ps1 -BotOnly    # Start Telegram bot only
#   .\Start-Mugen.ps1 -AdminOnly  # Start Admin Panel only
#   .\Start-Mugen.ps1 -Stop       # Kill all running MUGEN processes
#
# First time? Run this in your terminal:
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

param (
    [switch]$BotOnly,
    [switch]$AdminOnly,
    [switch]$Stop
)

# ==============================================================================
# Helpers
# ==============================================================================

function Write-Header {
    Clear-Host
    Write-Host ""
    Write-Host "  =================================================================" -ForegroundColor DarkGray
    Write-Host "   MUGEN AI  --  Autonomous Asset Request Bot" -ForegroundColor Cyan
    Write-Host "   Autonomous  *  Policy-Aware  *  Adversarially Hardened" -ForegroundColor DarkCyan
    Write-Host "  =================================================================" -ForegroundColor DarkGray
    Write-Host ""
}

function Write-Step {
    param([string]$Label, [string]$Msg)
    Write-Host "  [ $Label ]  $Msg" -ForegroundColor Cyan
}

function Write-OK {
    param([string]$Msg)
    Write-Host "     OK   $Msg" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Msg)
    Write-Host "     WARN $Msg" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Msg)
    Write-Host "     FAIL $Msg" -ForegroundColor Red
}

function Write-Sep {
    Write-Host "  -----------------------------------------------------------------" -ForegroundColor DarkGray
}

# ==============================================================================
# Resolve project root to the folder containing this script
# ==============================================================================
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Header

# ==============================================================================
# STOP mode
# ==============================================================================
if ($Stop) {
    Write-Step "STOP" "Killing MUGEN AI processes..."
    $killed = 0

    Get-Process -Name "python*" -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId=$($_.Id)" `
                        -ErrorAction SilentlyContinue).CommandLine
            if ($cmdLine -match "bot\.main|admin_panel\.run|admin_panel/run") {
                Stop-Process -Id $_.Id -Force
                Write-OK "Killed PID $($_.Id)"
                $killed++
            }
        } catch {}
    }

    if ($killed -eq 0) {
        Write-Warn "No MUGEN processes found running."
    } else {
        Write-OK "$killed process(es) stopped."
    }
    Write-Host ""
    exit 0
}

# ==============================================================================
# STEP 1 -- Locate Python
# ==============================================================================
Write-Step "1/5" "Checking Python installation..."

$python = $null
foreach ($candidate in @("python", "python3", "py")) {
    try {
        $ver = & $candidate --version 2>&1
        if ($ver -match "Python (\d+\.\d+)") {
            $python = $candidate
            Write-OK "Found $ver  (command: $candidate)"
            break
        }
    } catch { }
}

if (-not $python) {
    Write-Fail "Python not found. Install Python 3.11+ from https://python.org"
    exit 1
}

Write-Sep

# ==============================================================================
# STEP 2 -- Activate virtual environment
# ==============================================================================
Write-Step "2/5" "Looking for virtual environment..."

$venvPaths = @(
    ".venv\Scripts\Activate.ps1",
    "venv\Scripts\Activate.ps1",
    "env\Scripts\Activate.ps1"
)

$venvActivated = $false
foreach ($vp in $venvPaths) {
    $full = Join-Path $ProjectRoot $vp
    if (Test-Path $full) {
        Write-OK "Activating: $vp"
        & $full
        $python = "python"
        $venvActivated = $true
        break
    }
}

if (-not $venvActivated) {
    Write-Warn "No virtual environment found -- using system Python."
    Write-Warn "Tip: python -m venv .venv  then re-run this script."
}

Write-Sep

# ==============================================================================
# STEP 3 -- Validate .env file
# ==============================================================================
Write-Step "3/5" "Checking .env configuration..."

$envFile     = Join-Path $ProjectRoot ".env"
$exampleFile = Join-Path $ProjectRoot ".env.example"

if (-not (Test-Path $envFile)) {
    Write-Warn ".env not found."
    if (Test-Path $exampleFile) {
        Copy-Item $exampleFile $envFile
        Write-OK "Copied .env.example -> .env"
    } else {
        Write-Fail ".env.example is also missing. Cannot continue."
        exit 1
    }

    Write-Host ""
    Write-Host "  ACTION REQUIRED: Edit your .env and set these values:" -ForegroundColor Yellow
    Write-Host "    BOT_TOKEN       = <from @BotFather on Telegram>" -ForegroundColor White
    Write-Host "    GROQ_API_KEY    = <from console.groq.com>" -ForegroundColor White
    Write-Host "    ADMIN_USER_IDS  = <your Telegram numeric user ID>" -ForegroundColor White
    Write-Host ""
    $open = Read-Host "  Open .env in Notepad now? [Y/n]"
    if ($open -notmatch "^[Nn]") { Start-Process notepad $envFile; Start-Sleep 2 }

    $cont = Read-Host "  Continue startup after editing? [Y/n]"
    if ($cont -match "^[Nn]") { exit 1 }
}

# Parse .env into a hashtable (skip comments and blank lines)
$envMap = @{}
Get-Content $envFile |
    Where-Object { $_ -notmatch "^\s*#" -and $_ -match "=" } |
    ForEach-Object {
        $parts = $_ -split "=", 2
        $key   = $parts[0].Trim()
        $val   = ($parts[1] -split "#")[0].Trim()
        if ($key) { $envMap[$key] = $val }
    }

# Check required keys
$envOK = $true
foreach ($rk in @("BOT_TOKEN", "GROQ_API_KEY")) {
    $v = $envMap[$rk]
    if (-not $v -or $v -match "your_|<|>|placeholder|_here") {
        Write-Fail "$rk is not set in .env"
        $envOK = $false
    } else {
        $len    = $v.Length
        $masked = if ($len -gt 10) {
            $v.Substring(0,4) + ("*" * [Math]::Max(0, $len - 8)) + $v.Substring($len - 4)
        } else { "****" }
        Write-OK "$rk  = $masked"
    }
}

if (-not $envOK) {
    Write-Host ""
    Write-Warn "Missing keys detected. The bot may fail to start."
    Write-Warn "You can also set keys via the Admin Panel -> API Keys tab."
    $cont = Read-Host "  Continue anyway? [y/N]"
    if ($cont -notmatch "^[Yy]") { exit 1 }
}

if (-not $envMap["ADMIN_USER_IDS"]) {
    Write-Warn "ADMIN_USER_IDS not set -- admin bot commands will be unavailable."
} else {
    Write-OK "ADMIN_USER_IDS = $($envMap['ADMIN_USER_IDS'])"
}

Write-Sep

# ==============================================================================
# STEP 4 -- Ensure required directories exist
# ==============================================================================
Write-Step "4/5" "Checking project directories..."

$dirsNeeded = @("data", "rulebooks", "chroma_store")
foreach ($d in $dirsNeeded) {
    $full = Join-Path $ProjectRoot $d
    if (-not (Test-Path $full)) {
        New-Item -ItemType Directory -Path $full -Force | Out-Null
        Write-OK "Created : $d\"
    } else {
        Write-OK "Present : $d\"
    }
}

$hrisPath = Join-Path $ProjectRoot "data\hris.json"
if (-not (Test-Path $hrisPath)) {
    Write-Warn "data\hris.json not found -- employee table will be empty until you upload one."
}

Write-Sep

# ==============================================================================
# STEP 5 -- Check / install Python dependencies
# ==============================================================================
Write-Step "5/5" "Checking Python dependencies..."

$reqFile = Join-Path $ProjectRoot "requirements.txt"

if (-not (Test-Path $reqFile)) {
    Write-Warn "requirements.txt not found -- skipping dependency check."
} else {
    # Quick import probe for core packages
    $probe = & $python -c "import fastapi, telegram, aiosqlite, structlog, uvicorn; print('ok')" 2>&1
    if ($probe -match "^ok") {
        Write-OK "All core packages are installed."
    } else {
        Write-Warn "Some packages are missing. Running pip install..."
        Write-Host ""
        & $python -m pip install -r $reqFile
        if ($LASTEXITCODE -ne 0) {
            Write-Fail "pip install failed. Check your Python environment and try again."
            exit 1
        }
        Write-OK "Dependencies installed successfully."
    }
}

Write-Sep

# ==============================================================================
# Launch services in separate PowerShell windows
# ==============================================================================
$adminPort = if ($envMap["ADMIN_PORT"]) { $envMap["ADMIN_PORT"] } else { "8080" }

Write-Step "GO" "Launching services..."
Write-Host ""

# ── Telegram Bot window ───────────────────────────────────────────────────────
if (-not $AdminOnly) {
    $botTitle  = "MUGEN AI -- Telegram Bot"
    $botScript = @"
Set-Location '$ProjectRoot'
`$host.UI.RawUI.WindowTitle = '$botTitle'
Write-Host ''
Write-Host '  =================================================================' -ForegroundColor DarkGray
Write-Host '   MUGEN AI  --  Telegram Bot' -ForegroundColor Cyan
Write-Host '  =================================================================' -ForegroundColor DarkGray
Write-Host ''
python -m bot.main
Write-Host ''
Write-Host '  Bot stopped. Press Enter to close this window.' -ForegroundColor Yellow
Read-Host
"@
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $botScript
    Write-OK "Telegram Bot window launched."
    Start-Sleep -Milliseconds 600
}

# ── Admin Panel window ────────────────────────────────────────────────────────
if (-not $BotOnly) {
    $adminTitle  = "MUGEN AI -- Admin Panel :$adminPort"
    $adminScript = @"
Set-Location '$ProjectRoot'
`$host.UI.RawUI.WindowTitle = '$adminTitle'
Write-Host ''
Write-Host '  =================================================================' -ForegroundColor DarkGray
Write-Host '   MUGEN AI  --  Admin Panel' -ForegroundColor Magenta
Write-Host '   http://localhost:$adminPort' -ForegroundColor White
Write-Host '  =================================================================' -ForegroundColor DarkGray
Write-Host ''
python -m admin_panel.run
Write-Host ''
Write-Host '  Admin Panel stopped. Press Enter to close this window.' -ForegroundColor Yellow
Read-Host
"@
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $adminScript
    Write-OK "Admin Panel window launched."
    Start-Sleep -Milliseconds 600
}

# ==============================================================================
# Summary
# ==============================================================================
Write-Host ""
Write-Host "  =================================================================" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  MUGEN AI is starting up!" -ForegroundColor Green
Write-Host ""

if (-not $AdminOnly) {
    Write-Host "  Telegram Bot   --> running in separate window" -ForegroundColor Cyan
}
if (-not $BotOnly) {
    Write-Host "  Admin Panel    --> http://localhost:$adminPort" -ForegroundColor Magenta
}

Write-Host ""
Write-Host "  Useful commands:" -ForegroundColor DarkGray
Write-Host "    .\Start-Mugen.ps1             # Start both" -ForegroundColor Gray
Write-Host "    .\Start-Mugen.ps1 -BotOnly    # Bot only" -ForegroundColor Gray
Write-Host "    .\Start-Mugen.ps1 -AdminOnly  # Admin Panel only" -ForegroundColor Gray
Write-Host "    .\Start-Mugen.ps1 -Stop       # Kill all MUGEN processes" -ForegroundColor Gray
Write-Host ""
Write-Host "  Bot commands in Telegram:" -ForegroundColor DarkGray
Write-Host "    /request   Submit an asset request (asks for name + EMP ID first)" -ForegroundColor Gray
Write-Host "    /status    Check bot + RAG status" -ForegroundColor Gray
Write-Host "    /cancel    Cancel in-progress request" -ForegroundColor Gray
Write-Host ""
Write-Host "  =================================================================" -ForegroundColor DarkGray
Write-Host ""
