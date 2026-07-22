# ==============================================================================
#      A B Y S S   C Y B E R   S E N T I N E L   I N S T A L L E R
# ==============================================================================
# 1-Line Global Terminal Installer for Windows (Claude Code style)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "     A B Y S S   C Y B E R   S E N T I N E L   I N S T A L L E R" -ForegroundColor Cyan
Write-Host "     System Incident Response & Compromise Remediation Engine v1.0" -ForegroundColor White
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python installation
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[!] Error: Python 3 is not installed or not in system PATH." -ForegroundColor Red
    Write-Host "[!] Please install Python 3.8+ from https://python.org and try again." -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/2] Installing ABYSS CLI executable & threat signatures..." -ForegroundColor Yellow
python -m pip install --upgrade --no-cache-dir git+https://github.com/pintudevv/ABYSS.git

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==============================================================================" -ForegroundColor Green
    Write-Host " [OK] SUCCESS: ABYSS Cyber Incident Sentinel is installed!" -ForegroundColor Green
    Write-Host "==============================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Type 'abyss' in any terminal window to launch the security scanner." -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host "[!] Installation failed. Please check your internet connection or git/python setup." -ForegroundColor Red
}
