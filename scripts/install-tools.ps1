# install-tools.ps1
# Run from PowerShell as Administrator:
#   Set-ExecutionPolicy Bypass -Scope Process -Force; .\scripts\install-tools.ps1

$ErrorActionPreference = "Stop"

function Test-Command($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Write-Step($msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

function Write-Ok($msg) {
    Write-Host "  [OK] $msg" -ForegroundColor Green
}

function Write-Skip($msg) {
    Write-Host "  [SKIP] $msg (already installed)" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# winget (required to install other tools)
# ---------------------------------------------------------------------------
Write-Step "Checking winget..."
if (-not (Test-Command winget)) {
    Write-Host "  winget not found. Install 'App Installer' from the Microsoft Store, then re-run this script." -ForegroundColor Red
    exit 1
}
Write-Ok "winget found"

# ---------------------------------------------------------------------------
# Node.js (includes npm)
# ---------------------------------------------------------------------------
Write-Step "Checking Node.js / npm..."
if (Test-Command node) {
    $nodeVer = (node --version)
    Write-Skip "Node.js $nodeVer"
} else {
    Write-Host "  Installing Node.js LTS via winget..."
    winget install --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
    Write-Ok "Node.js installed"
    # Refresh PATH for this session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# ---------------------------------------------------------------------------
# uv (Python package manager)
# ---------------------------------------------------------------------------
Write-Step "Checking uv..."
if (Test-Command uv) {
    $uvVer = (uv --version)
    Write-Skip "uv $uvVer"
} else {
    Write-Host "  Installing uv via official installer..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    # Refresh PATH for this session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
    Write-Ok "uv installed"
}

# ---------------------------------------------------------------------------
# make (GnuWin32)
# ---------------------------------------------------------------------------
Write-Step "Checking make..."
if (Test-Command make) {
    $makeVer = (make --version | Select-Object -First 1)
    Write-Skip "make ($makeVer)"
} else {
    Write-Host "  Installing make via winget..."
    winget install --id GnuWin32.Make --accept-source-agreements --accept-package-agreements
    # GnuWin32 installs to Program Files; add to PATH for this session
    $gnuPath = "C:\Program Files (x86)\GnuWin32\bin"
    if (Test-Path $gnuPath) {
        $env:Path += ";$gnuPath"
        # Persist for the current user
        $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
        if ($userPath -notlike "*GnuWin32*") {
            [System.Environment]::SetEnvironmentVariable("Path", "$userPath;$gnuPath", "User")
        }
    }
    Write-Ok "make installed"
}

# ---------------------------------------------------------------------------
# Docker Desktop (optional — needed for Qdrant + Neo4j)
# ---------------------------------------------------------------------------
Write-Step "Checking Docker..."
if (Test-Command docker) {
    $dockerVer = (docker --version)
    Write-Skip "Docker ($dockerVer)"
} else {
    $ans = Read-Host "  Docker not found. Install Docker Desktop? [y/N]"
    if ($ans -match "^[Yy]$") {
        winget install --id Docker.DockerDesktop --accept-source-agreements --accept-package-agreements
        Write-Ok "Docker Desktop installed (restart may be required)"
    } else {
        Write-Host "  Skipping Docker. You will need it to run Qdrant and Neo4j." -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host "`n===== All done! =====" -ForegroundColor Green
Write-Host "Close and reopen PowerShell so PATH changes take effect, then run:"
Write-Host ""
Write-Host "  uv sync                                          # install Python deps"
Write-Host "  docker compose -f docker/docker-compose.yml up -d  # start Qdrant + Neo4j"
Write-Host "  cd electron && npm install && npm run dev        # run the app"
Write-Host ""
