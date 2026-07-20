"""
ABYSS — ZIP/Archive Analyzer
==============================
Analyzes ZIP archives for malicious content using heuristic rules.

Detects:
  - Malicious files inside (.exe, .dll, .bat, .vbs, .ps1, .js, .hta, .cmd)
  - Path traversal attacks (../../etc/passwd)
  - Zip bombs (high compression ratio, nested archives)
  - Password-protected entries (hiding malware)
  - Suspicious file count / naming patterns
  - Embedded executables disguised as other types
  - Macros in Office documents (inside ZIP)

Output: features.json compatible with classifier.py
"""

import json
import math
import re
import hashlib
import zipfile
import logging
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from shared_types import get_empty_pe_analysis, get_base_heuristic_risk

log = logging.getLogger("zip_analyzer")

# ---------------------------------------------------------------------------
# Suspicious indicators
# ---------------------------------------------------------------------------
CRITICAL_EXTENSIONS = {
    ".exe", ".dll", ".scr", ".pif", ".com", ".vbs", ".vbe", ".hta", ".lnk"
}

SUSPICIOUS_EXTENSIONS = {
    ".bat", ".cmd", ".ps1", ".ps2", ".psm1", ".psd1",
    ".msi", ".msp", ".msc", ".reg", ".js", ".jse",
    ".ws", ".wsh", ".inf", ".jar", ".war", ".ear"
}

OFFICE_MACRO_PATHS = {
    "word/vbaproject.bin",
    "xl/vbaproject.bin",
    "ppt/vbaproject.bin",
    "macros/vba",
}

SUSPICIOUS_FILENAMES = re.compile(
    r"(invoice|receipt|payment|order|confirm|statement|document|update|patch|crack|keygen|serial|activation)",
    re.IGNORECASE
)

PATH_TRAVERSAL = re.compile(r"\.\.[/\\]")

DOUBLE_EXTENSION = re.compile(
    r"\.(pdf|doc|docx|xls|xlsx|jpg|png|txt)\.(exe|bat|vbs|js|ps1|cmd|scr)$",
    re.IGNORECASE
)

ZIP_BOMB_COMPRESSION_RATIO = 100  # compressed size * ratio < uncompressed = suspicious


def _entropy(data: bytes) -> float:
    if not data:
        return 0.0
    freq: dict[int, int] = {}
    for b in data:
        freq[b] = freq.get(b, 0) + 1
    total = len(data)
    return -sum((c / total) * math.log2(c / total) for c in freq.values())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _is_pe(header: bytes) -> bool:
    return header[:2] == b"MZ"


def analyze_zip(file_path: Path, output_dir: Path) -> dict[str, Any]:
    log.info("Starting ZIP analysis of: %s (%s bytes)", file_path.name, file_path.stat().st_size)

    data = file_path.read_bytes()
    sha256 = _sha256(data)
    md5    = _md5(data)
    size   = len(data)

    # ---- Parse ZIP ----
    is_valid_zip = zipfile.is_zipfile(file_path)
    entries: list[dict[str, Any]] = []
    critical_files: list[str] = []
    suspicious_ext_files: list[str] = []
    suspicious_files: list[str] = []
    path_traversal_files: list[str] = []
    double_ext_files: list[str] = []
    encrypted_entries: list[str] = []
    nested_archives: list[str] = []
    has_macros = False
    max_compression_ratio = 0.0
    is_zip_bomb = False
    total_uncompressed = 0
    total_compressed = size
    embedded_pe_files: list[str] = []
    office_extensions = {".docx", ".xlsx", ".pptx", ".docm", ".xlsm", ".pptm"}
    is_office_doc = file_path.suffix.lower() in office_extensions

    if is_valid_zip:
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                for info in zf.infolist():
                    name = info.filename
                    ext  = Path(name).suffix.lower()
                    compressed   = info.compress_size
                    uncompressed = info.file_size
                    total_uncompressed += uncompressed

                    entry: dict[str, Any] = {
                        "name":         name,
                        "size":         uncompressed,
                        "compressed":   compressed,
                        "extension":    ext,
                        "is_encrypted": bool(info.flag_bits & 0x1),
                    }
                    entries.append(entry)

                    # Encrypted
                    if info.flag_bits & 0x1:
                        encrypted_entries.append(name)

                    # Path traversal
                    if PATH_TRAVERSAL.search(name):
                        path_traversal_files.append(name)

                    # Double extension
                    if DOUBLE_EXTENSION.search(name):
                        double_ext_files.append(name)

                    # Critical / Suspicious extension checks
                    if ext in CRITICAL_EXTENSIONS:
                        critical_files.append(name)
                    elif ext in SUSPICIOUS_EXTENSIONS:
                        suspicious_ext_files.append(name)

                    # Nested archives
                    if ext in {".zip", ".rar", ".7z", ".gz", ".tar", ".bz2"}:
                        nested_archives.append(name)

                    # Office macros
                    if name.lower() in OFFICE_MACRO_PATHS:
                        has_macros = True

                    # Zip bomb detection
                    if compressed > 0:
                        ratio = uncompressed / compressed
                        if ratio > max_compression_ratio:
                            max_compression_ratio = ratio
                        if ratio > ZIP_BOMB_COMPRESSION_RATIO and uncompressed > 1_000_000:
                            is_zip_bomb = True

                    # Suspicious filenames (social engineering)
                    if SUSPICIOUS_FILENAMES.search(Path(name).stem):
                        if name not in critical_files and name not in suspicious_ext_files:
                            suspicious_files.append(name)

                    # Read first bytes to check for PE magic (disguised executables)
                    if ext not in CRITICAL_EXTENSIONS and ext not in SUSPICIOUS_EXTENSIONS and not info.is_dir():
                        try:
                            header = zf.read(name)[:4]
                            if _is_pe(header):
                                embedded_pe_files.append(name)
                        except Exception:
                            pass

        except zipfile.BadZipFile:
            is_valid_zip = False
            log.warning("File claims to be ZIP but is malformed")
        except Exception as e:
            log.warning("ZIP read error: %s", e)

    malicious_files = critical_files + suspicious_ext_files

    # ---- Heuristic scoring ----
    score = 0
    reasons: list[str] = []

    if critical_files:
        score += 45
        reasons.append(f"Critical execution files inside: {critical_files[:5]} (+45)")

    # Check if archive is a legitimate web/software source code repository
    is_source_repository = any(
        Path(e["name"]).name.lower() in {"package.json", "tsconfig.json", "jsconfig.json", "cargo.toml", "pyproject.toml", "go.mod", "webpack.config.js", "craco.config.js"}
        for e in entries
    )

    if is_source_repository:
        # Exclude standard web/app source code JS files from suspicious script count
        suspicious_ext_files = [f for f in suspicious_ext_files if not f.lower().endswith((".js", ".jsx", ".ts", ".tsx"))]

    if suspicious_ext_files:
        score += 15
        reasons.append(f"Suspicious script/installer files inside: {suspicious_ext_files[:5]} (+15)")

    if embedded_pe_files:
        score += 35
        reasons.append(f"Disguised executables (PE header in non-exe): {embedded_pe_files[:3]} (+35)")

    if path_traversal_files:
        score += 30
        reasons.append(f"Path traversal attack detected: {path_traversal_files[:3]} (+30)")

    if is_zip_bomb:
        score += 25
        reasons.append(f"Zip bomb detected (compression ratio {max_compression_ratio:.0f}x) (+25)")

    if double_ext_files:
        score += 25
        reasons.append(f"Double extension files (disguised): {double_ext_files[:3]} (+25)")

    if has_macros and not is_office_doc:
        score += 20
        reasons.append("VBA macro binary found in non-Office archive (+20)")
    elif has_macros:
        score += 10
        reasons.append("VBA macro binary found in Office document (+10)")

    if encrypted_entries:
        score += 10
        reasons.append(f"{len(encrypted_entries)} encrypted entries (hiding content) (+10)")

    if nested_archives:
        score += 5
        reasons.append(f"Nested archives inside: {nested_archives[:3]} (+5)")

    if suspicious_files:
        score += 5
        reasons.append(f"Socially engineered filenames: {suspicious_files[:3]} (+5)")

    score = min(score, 100)

    risk_level = (
        "CRITICAL" if score >= 80 else
        "HIGH"     if score >= 60 else
        "MEDIUM"   if score >= 40 else
        "LOW"      if score >= 20 else
        "CLEAN"
    )

    # ---- Build features.json ----
    features = {
        "file_info": {
            "filename":           file_path.name,
            "filepath":           str(file_path),
            "file_size_bytes":    size,
            "file_size_kb":       round(size / 1024, 2),
            "md5":                md5,
            "sha256":             sha256,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "file_type":          "ZIP",
        },
        "file_type": {
            "mime":               "application/zip",
            "description":        f"ZIP archive ({len(entries)} entries)",
            "is_pe":              False,
            "is_pdf":             False,
            "is_zip":             True,
            "extension":          file_path.suffix.lower(),
        },
        "zip_analysis": {
            "is_valid_zip":          is_valid_zip,
            "entry_count":           len(entries),
            "total_uncompressed_kb": round(total_uncompressed / 1024, 2),
            "max_compression_ratio": round(max_compression_ratio, 2),
            "is_zip_bomb":           is_zip_bomb,
            "malicious_files":       malicious_files,
            "embedded_pe_files":     embedded_pe_files,
            "path_traversal_files":  path_traversal_files,
            "double_ext_files":      double_ext_files,
            "encrypted_entries":     encrypted_entries,
            "nested_archives":       nested_archives,
            "has_macros":            has_macros,
            "suspicious_files":      suspicious_files,
            "entries_sample":        entries[:20],
        },
        "string_analysis": {
            "urls_found":      [],
            "suspicious_hits": [{"pattern": f, "context": "zip_entry"} for f in malicious_files],
            "total_strings":   len(entries),
        },
        "heuristic_risk": get_base_heuristic_risk(score, risk_level, reasons),
        "pe_analysis": get_empty_pe_analysis(),
    }

    output_path = output_dir / "features.json"
    output_path.write_text(json.dumps(features, indent=2), encoding="utf-8")
    log.info("ZIP analysis complete. Score: %d/100 [%s]", score, risk_level)
    return features


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    parser = argparse.ArgumentParser(description="ABYSS ZIP Analyzer")
    parser.add_argument("file", help="ZIP file to analyze")
    parser.add_argument("--output", default="results", help="Output directory")
    args = parser.parse_args()

    file_path  = Path(args.file)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not file_path.exists():
        log.error("File not found: %s", file_path)
        return 1

    features = analyze_zip(file_path, output_dir)
    risk = features["heuristic_risk"]

    print("\n" + "=" * 60)
    print("  ABYSS — ZIP ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"  File    : {file_path.name}")
    print(f"  Entries : {features['zip_analysis']['entry_count']}")
    print(f"  Score   : {risk['score']}/100  [{risk['risk_level']}]")
    if risk["reasons"]:
        print("  Flags   :")
        for r in risk["reasons"]:
            print(f"    • {r}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
