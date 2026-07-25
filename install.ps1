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
python -m pip install --upgrade abyss-security

if ($LASTEXITCODE -eq 0) {
    Write-Host "[2/2] Verifying Python Scripts PATH configuration..." -ForegroundColor Yellow
    try {
        $scriptsDir = python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
        if ($scriptsDir -and (Test-Path $scriptsDir)) {
            $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
            if ($userPath -notlike "*$scriptsDir*") {
                [Environment]::SetEnvironmentVariable("Path", "$userPath;$scriptsDir", "User")
                $env:Path += ";$scriptsDir"
                Write-Host "[+] Automatically added Python Scripts ($scriptsDir) to User PATH." -ForegroundColor Green
            }
        }
    } catch {}

    Write-Host ""
    Write-Host "==============================================================================" -ForegroundColor Green
    Write-Host " [OK] SUCCESS: ABYSS Cyber Incident Sentinel is installed!" -ForegroundColor Green
    Write-Host "==============================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Type 'abyss' in any new terminal window to launch the security scanner." -ForegroundColor Cyan
    Write-Host "  (If 'abyss' is not recognized, restart terminal or run: python -m abyss)" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "[!] Installation failed. Please check your internet connection or git/python setup." -ForegroundColor Red
}
