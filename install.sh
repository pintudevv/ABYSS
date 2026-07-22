#!/bin/bash
# ==============================================================================
#      A B Y S S   C Y B E R   S E N T I N E L   I N S T A L L E R
# ==============================================================================
# 1-Line Global Terminal Installer for Linux & macOS (Claude Code style)

set -e

echo ""
echo "=============================================================================="
echo "     A B Y S S   C Y B E R   S E N T I N E L   I N S T A L L E R"
echo "     System Incident Response & Compromise Remediation Engine v1.0"
echo "=============================================================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[!] Error: python3 is not installed or not in PATH."
    exit 1
fi

echo "[1/2] Installing ABYSS CLI executable & threat signatures..."
python3 -m pip install --upgrade --no-cache-dir git+https://github.com/pintudevv/ABYSS.git

echo ""
echo "=============================================================================="
echo " [OK] SUCCESS: ABYSS Cyber Incident Sentinel is installed!"
echo "=============================================================================="
echo ""
echo "  Type 'abyss' in any terminal window to launch the security scanner."
echo ""
