"""
ABYSS — PDF Analyzer
=====================
Extracts malicious indicators from PDF files using heuristic rules.

Detects:
  - Embedded JavaScript (/JS, /JavaScript)
  - Auto-action triggers (/AA, /OpenAction)
  - Launch/URI/SubmitForm/ImportData actions
  - Embedded executables or streams
  - Encrypted/obfuscated content
  - Suspicious string patterns
  - Abnormal object counts
  - High-entropy streams (shellcode indicator)

Output: features.json compatible with classifier.py
"""

import json
import math
import re
import hashlib
import logging
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("pdf_analyzer")

# ---------------------------------------------------------------------------
# PDF suspicious indicators
# ---------------------------------------------------------------------------
SUSPICIOUS_PDF_KEYS = [
    "/JS", "/JavaScript",          # Embedded JS
    "/AA", "/OpenAction",          # Auto-actions on open
    "/Launch",                     # Launch external app
    "/URI",                        # URL trigger
    "/SubmitForm",                 # Data exfiltration
    "/ImportData",                 # Import external data
    "/RichMedia",                  # Flash/multimedia embedding
    "/XFA",                        # XML Forms Architecture (exploitable)
    "/ObjStm",                     # Object streams (obfuscation)
    "/XObject",                    # Embedded objects
    "/EmbeddedFile",               # File attachments
    "/Encrypt",                    # Encrypted content
    "/AcroForm",                   # Interactive forms
    "/JBIG2Decode",                # JBIG2 exploit vector
    "/FlateDecode",                # Compressed streams
    "/ASCIIHexDecode",             # Hex-encoded content
    "/ASCII85Decode",              # Base85 encoding
    "/RunLengthDecode",            # Run-length (rare, suspicious)
    "/CCITTFaxDecode",             # Fax encoding (unusual)
]

CRITICAL_PDF_KEYS = {
    "/JS", "/JavaScript", "/AA", "/OpenAction",
    "/Launch", "/SubmitForm", "/ImportData"
}

SUSPICIOUS_JS_PATTERNS = [
    r"eval\s*\(",
    r"unescape\s*\(",
    r"String\.fromCharCode",
    r"document\.write",
    r"this\.exportDataObject",
    r"app\.launchURL",
    r"util\.printf",          # CVE-2008-2992 printf exploit
    r"Collab\.collectEmailInfo",
    r"media\.newPlayer",
    r"spell\.customDictionaryOpen",
    r"app\.openDoc",
    r"xfa\.host",
]

SUSPICIOUS_URL_PATTERN = re.compile(
    r'(https?://|ftp://|\\\\[a-zA-Z0-9])[^\s\x00-\x1f"\'<>]{4,}',
    re.IGNORECASE
)


def _entropy(data: bytes) -> float:
    if not data:
        return 0.0
    freq = {}
    for b in data:
        freq[b] = freq.get(b, 0) + 1
    total = len(data)
    return -sum((c / total) * math.log2(c / total) for c in freq.values())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def analyze_pdf(file_path: Path, output_dir: Path) -> dict[str, Any]:
    log.info("Starting PDF analysis of: %s (%s bytes)", file_path.name, file_path.stat().st_size)

    data = file_path.read_bytes()
    text = data.decode("latin-1", errors="replace")  # PDF is latin-1 safe

    # ---- File info ----
    sha256 = _sha256(data)
    md5    = _md5(data)
    size   = len(data)

    # ---- PDF structure checks ----
    is_pdf = text[:5] == "%PDF-"
    version = ""
    if is_pdf:
        m = re.match(r"%PDF-(\d+\.\d+)", text)
        version = m.group(1) if m else "unknown"

    # ---- Object count ----
    obj_count   = len(re.findall(r"\d+\s+\d+\s+obj", text))
    endobj_count = text.count("endobj")
    stream_count = text.count("stream")

    # ---- Suspicious key detection ----
    found_keys: list[str] = []
    for key in SUSPICIOUS_PDF_KEYS:
        if key in text:
            found_keys.append(key)

    critical_keys = [k for k in found_keys if k in CRITICAL_PDF_KEYS]

    # ---- JavaScript extraction & pattern matching ----
    js_snippets: list[str] = []
    js_pattern_hits: list[str] = []

    # Extract JS content between stream/endstream
    stream_blocks = re.findall(r"stream\r?\n(.*?)\r?\nendstream", text, re.DOTALL)
    for block in stream_blocks:
        for pat in SUSPICIOUS_JS_PATTERNS:
            if re.search(pat, block, re.IGNORECASE):
                js_pattern_hits.append(pat)
                js_snippets.append(block[:200])

    # Direct JS keyword search
    for pat in SUSPICIOUS_JS_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            if pat not in js_pattern_hits:
                js_pattern_hits.append(pat)

    # ---- URL extraction ----
    urls_found = list(set(SUSPICIOUS_URL_PATTERN.findall(text)))[:20]

    # ---- Embedded file detection ----
    has_embedded_exe = bool(re.search(r"MZ|PE\x00\x00", text[:65536]))
    embedded_extensions = list(set(re.findall(r"\.(exe|dll|bat|vbs|ps1|js|py|sh|cmd)\b", text, re.IGNORECASE)))

    # ---- Encryption / obfuscation ----
    is_encrypted = "/Encrypt" in text
    has_obfuscated_streams = "/ObjStm" in text or "/ASCIIHexDecode" in text

    # ---- Stream entropy analysis (detect shellcode) ----
    max_stream_entropy = 0.0
    high_entropy_streams = 0
    for block in stream_blocks[:20]:  # Sample first 20 streams
        e = _entropy(block.encode("latin-1", errors="replace"))
        if e > max_stream_entropy:
            max_stream_entropy = e
        if e > 7.0:
            high_entropy_streams += 1

    # ---- Heuristic scoring ----
    score = 0
    reasons: list[str] = []

    if critical_keys:
        score += 35
        reasons.append(f"Critical PDF action keys found: {', '.join(critical_keys)} (+35)")

    if js_pattern_hits:
        score += 25
        reasons.append(f"Suspicious JS patterns: {len(js_pattern_hits)} matches (+25)")

    if has_embedded_exe:
        score += 30
        reasons.append("Embedded executable (MZ/PE header) found (+30)")

    if embedded_extensions:
        score += 20
        reasons.append(f"Suspicious embedded extensions: {embedded_extensions} (+20)")

    if is_encrypted:
        score += 10
        reasons.append("PDF is encrypted/obfuscated (+10)")

    if has_obfuscated_streams:
        score += 10
        reasons.append("Obfuscated object streams (/ObjStm or ASCII hex) (+10)")

    if high_entropy_streams > 0:
        score += 15
        reasons.append(f"{high_entropy_streams} high-entropy stream(s) — possible shellcode (+15)")

    if urls_found:
        score += 5
        reasons.append(f"{len(urls_found)} URL(s) found in PDF (+5)")

    if len(found_keys) > 5:
        score += 5
        reasons.append(f"Abnormal number of suspicious PDF keys ({len(found_keys)}) (+5)")

    score = min(score, 100)

    risk_level = (
        "CRITICAL" if score >= 80 else
        "HIGH"     if score >= 60 else
        "MEDIUM"   if score >= 40 else
        "LOW"      if score >= 20 else
        "CLEAN"
    )

    # ---- Build features.json (compatible with classifier.py) ----
    features = {
        "file_info": {
            "filename":           file_path.name,
            "filepath":           str(file_path),
            "file_size_bytes":    size,
            "file_size_kb":       round(size / 1024, 2),
            "md5":                md5,
            "sha256":             sha256,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "file_type":          "PDF",
        },
        "file_type": {
            "mime":               "application/pdf",
            "description":        f"PDF document version {version}",
            "is_pe":              False,
            "is_pdf":             is_pdf,
            "is_zip":             False,
            "extension":          ".pdf",
        },
        "pdf_analysis": {
            "is_valid_pdf":           is_pdf,
            "pdf_version":            version,
            "object_count":           obj_count,
            "stream_count":           stream_count,
            "is_encrypted":           is_encrypted,
            "has_obfuscated_streams": has_obfuscated_streams,
            "has_embedded_exe":       has_embedded_exe,
            "embedded_extensions":    embedded_extensions,
            "suspicious_keys":        found_keys,
            "critical_keys":          critical_keys,
            "js_pattern_hits":        js_pattern_hits,
            "js_snippets":            js_snippets[:3],
            "urls_found":             urls_found,
            "max_stream_entropy":     round(max_stream_entropy, 4),
            "high_entropy_streams":   high_entropy_streams,
        },
        "string_analysis": {
            "urls_found":       urls_found,
            "suspicious_hits":  [{"pattern": p, "context": ""} for p in js_pattern_hits],
            "total_strings":    len(re.findall(r'[\x20-\x7e]{4,}', text)),
        },
        "heuristic_risk": {
            "score":      score,
            "risk_level": risk_level,
            "reasons":    reasons,
        },
        # Stub PE fields so classifier.py doesn't crash on missing keys
        "pe_analysis": {
            "is_valid_pe":          False,
            "sections":             [],
            "imports":              {},
            "dangerous_imports":    [],
            "suspicious_import_count": 0,
            "total_import_count":   0,
            "is_packed":            False,
            "overall_entropy":      round(max_stream_entropy, 4),
            "tls_callbacks":        [],
            "has_overlay":          False,
        },
    }

    output_path = output_dir / "features.json"
    output_path.write_text(json.dumps(features, indent=2), encoding="utf-8")
    log.info("PDF analysis complete. Score: %d/100 [%s]", score, risk_level)
    log.info("Output: %s", output_path)
    return features


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    parser = argparse.ArgumentParser(description="ABYSS PDF Analyzer")
    parser.add_argument("file", help="PDF file to analyze")
    parser.add_argument("--output", default="results", help="Output directory")
    args = parser.parse_args()

    file_path  = Path(args.file)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not file_path.exists():
        log.error("File not found: %s", file_path)
        return 1

    features = analyze_pdf(file_path, output_dir)
    risk = features["heuristic_risk"]

    print("\n" + "=" * 60)
    print("  ABYSS — PDF ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"  File  : {file_path.name}")
    print(f"  Score : {risk['score']}/100  [{risk['risk_level']}]")
    if risk["reasons"]:
        print("  Flags :")
        for r in risk["reasons"]:
            print(f"    • {r}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
