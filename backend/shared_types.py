"""
Shared type definitions and constants for ABYSS analyzers.
Eliminates duplication of pe_analysis stubs across pdf_analyzer.py, zip_analyzer.py, etc.
"""

from typing import Any, Dict


def get_empty_pe_analysis(overall_entropy: float = 0.0) -> Dict[str, Any]:
    """Return a standard empty PE analysis dict for non-PE files."""
    return {
        "is_valid_pe": False,
        "sections": [],
        "imports": {},
        "dangerous_imports": [],
        "suspicious_import_count": 0,
        "total_import_count": 0,
        "is_packed": False,
        "overall_entropy": overall_entropy,
        "tls_callbacks": [],
        "has_overlay": False,
    }


def get_base_file_info(filename: str, filepath: str, size: int, md5: str, sha256: str) -> Dict[str, Any]:
    """Build standard file_info dict."""
    from datetime import datetime, timezone
    return {
        "filename": filename,
        "filepath": filepath,
        "file_size_bytes": size,
        "file_size_kb": round(size / 1024, 2),
        "md5": md5,
        "sha256": sha256,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_base_heuristic_risk(score: int, risk_level: str, reasons: list) -> Dict[str, Any]:
    """Build standard heuristic_risk dict."""
    return {
        "score": score,
        "risk_level": risk_level,
        "reasons": reasons,
    }