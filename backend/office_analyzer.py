"""
ABYSS — Office Document Exploit Analyzer (.docx, .xlsx, .doc, .xls)
====================================================================
Detects malicious VBA macros, AutoOpen triggers, PowerShell launchers,
WScript execution streams, and obfuscated payload drops in Office files.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Dict, Any, List

OFFICE_SUSPICIOUS_KEYWORDS = [
    "autoopen", "document_open", "workbook_open", "autoexec",
    "wscript.shell", "shell.application", "powershell", "cmd.exe",
    "createobject", "winmgmts", "callwindowproc", "virtualalloc",
    "writeprocessmemory", "createremotethread", "base64", "http-request"
]

def analyze_office_file(file_path: str) -> Dict[str, Any]:
    p = Path(file_path)
    if not p.exists():
        return {"error": "File not found", "risk_score": 0}

    findings: List[str] = []
    risk_score = 0
    has_vba_macros = False

    # Inspect ZIP structure (.docx, .xlsx, .xlsm, .docm)
    if zipfile.is_zipfile(file_path):
        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                names = z.namelist()
                vba_files = [n for n in names if "vbaProject.bin" in n or "vba" in n.lower() or "macros" in n.lower()]
                if vba_files:
                    has_vba_macros = True
                    risk_score += 40
                    findings.append(f"VBA Macro Binary Stream Detected ({', '.join(vba_files)})")

                # Inspect XML streams for suspicious commands
                for name in names:
                    if name.endswith(".xml") or name.endswith(".rels"):
                        try:
                            content = z.read(name).decode('utf-8', errors='ignore').lower()
                            for kw in OFFICE_SUSPICIOUS_KEYWORDS:
                                if kw in content:
                                    risk_score += 15
                                    findings.append(f"Suspicious Macro Keyword in XML Stream '{name}': '{kw}'")
                                    break
                        except Exception:
                            pass
        except Exception:
            pass

    # Read binary for legacy format .doc / .xls or raw stream scan
    try:
        raw_bytes = p.read_bytes()
        raw_str = raw_bytes.decode('latin1', errors='ignore').lower()
        for kw in OFFICE_SUSPICIOUS_KEYWORDS:
            if kw in raw_str and kw not in " ".join(findings):
                risk_score += 15
                findings.append(f"Malicious Execution Signature Discovered: '{kw}'")
    except Exception:
        pass

    risk_score = min(risk_score, 100)
    risk_level = "CRITICAL" if risk_score >= 70 else "HIGH" if risk_score >= 40 else "MEDIUM" if risk_score >= 20 else "CLEAN"

    return {
        "file_name": p.name,
        "file_size": p.stat().st_size,
        "has_vba_macros": has_vba_macros,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "is_malicious": risk_score >= 40,
        "findings": findings,
        "recommendation": "DO NOT ENABLE MACROS! Document contains malicious macro code." if risk_score >= 40 else "Document streams clean."
    }
