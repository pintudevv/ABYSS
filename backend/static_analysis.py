"""
StealthOS — Static Feature Extractor (Step 1)
==============================================
Extracts static features from EXE or ZIP files using:
  - pefile  : PE header, imports, sections, entropy
  - python-magic : true file type detection
  - LIEF    : deep binary analysis

Output: features.json in results/ directory
"""

import os
import sys
import json
import math
import hashlib
import zipfile
import struct
import string
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# Graceful optional-import wrappers
# ---------------------------------------------------------------------------
try:
    import pefile
    HAS_PEFILE = True
except ImportError:
    HAS_PEFILE = False
    logging.warning("pefile not installed — PE analysis will be skipped. Run: pip install pefile")

try:
    import lief
    HAS_LIEF = True
except ImportError:
    HAS_LIEF = False
    logging.warning("lief not installed — deep binary analysis will be skipped. Run: pip install lief")

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    logging.warning("python-magic not installed — file-type detection will use extension fallback. Run: pip install python-magic")

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("static_analysis")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Strings that are common indicators of compromise
SUSPICIOUS_STRINGS = [
    # Network / C2
    "http://", "https://", "ftp://", "ws://",
    "socket", "connect", "bind", "listen",
    "WSAStartup", "WinHttpOpen", "InternetOpen",
    # Crypto / ransomware
    "CryptEncrypt", "CryptDecrypt", "CryptGenKey",
    "AES", "RSA", "encrypt", "decrypt",
    "ransom", "bitcoin", "wallet",
    # Credential theft
    "password", "passwd", "credential",
    "GetClipboardData", "keylog",
    "LSASS", "SAM", "ntds",
    # Persistence
    "HKEY_LOCAL_MACHINE", "HKLM", "HKCU",
    "Run", "RunOnce", "Startup",
    "schtasks", "crontab", "Task Scheduler",
    # Process injection
    "VirtualAlloc", "VirtualAllocEx",
    "WriteProcessMemory", "CreateRemoteThread",
    "NtUnmapViewOfSection", "QueueUserAPC",
    # Anti-analysis
    "IsDebuggerPresent", "CheckRemoteDebuggerPresent",
    "NtQueryInformationProcess", "GetTickCount",
    "sleep", "Sleep", "anti-analysis",
    # File system
    "DeleteFile", "MoveFile", "CopyFile",
    ".exe", ".dll", ".bat", ".ps1", ".vbs",
    # Shell / execution
    "cmd.exe", "powershell", "wscript", "cscript",
    "ShellExecute", "CreateProcess", "WinExec",
    # Packing indicators
    "UPX", "MPRESS", "Themida", "VMProtect",
]

# Dangerous imported DLLs / functions
DANGEROUS_IMPORTS = {
    "kernel32.dll": [
        "VirtualAlloc", "VirtualAllocEx", "VirtualProtect",
        "WriteProcessMemory", "ReadProcessMemory",
        "CreateRemoteThread", "OpenProcess",
        "CreateProcess", "WinExec",
        "DeleteFileA", "DeleteFileW",
        "MoveFileExA", "MoveFileExW",
        "CopyFileA", "CopyFileW",
    ],
    "advapi32.dll": [
        "RegSetValueEx", "RegCreateKey", "RegOpenKey",
        "CryptEncrypt", "CryptDecrypt", "CryptGenKey",
        "LookupPrivilegeValue", "AdjustTokenPrivileges",
    ],
    "user32.dll": [
        "GetClipboardData", "SetClipboardData",
        "GetAsyncKeyState", "SetWindowsHookEx",
        "SendInput",
    ],
    "ws2_32.dll": [
        "connect", "bind", "listen", "send", "recv",
        "WSASend", "WSARecv", "WSAConnect",
    ],
    "wininet.dll": [
        "InternetOpen", "InternetConnect",
        "InternetOpenUrl", "HttpSendRequest",
        "InternetReadFile",
    ],
    "ntdll.dll": [
        "NtUnmapViewOfSection", "NtWriteVirtualMemory",
        "NtCreateThreadEx", "RtlDecompressBuffer",
        "NtQueryInformationProcess",
    ],
    "psapi.dll": [
        "EnumProcessModules", "GetModuleFileNameEx",
    ],
}


# ===========================================================================
# Utility helpers
# ===========================================================================

def compute_hashes(file_path: Path) -> dict:
    """Return MD5, SHA1, SHA256 of a file."""
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            md5.update(chunk)
            sha1.update(chunk)
            sha256.update(chunk)
    return {
        "md5": md5.hexdigest(),
        "sha1": sha1.hexdigest(),
        "sha256": sha256.hexdigest(),
    }


def compute_entropy(data: bytes) -> float:
    """Compute Shannon entropy of a byte sequence."""
    if not data:
        return 0.0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    length = len(data)
    entropy = 0.0
    for count in freq:
        if count:
            p = count / length
            entropy -= p * math.log2(p)
    return round(entropy, 4)


def extract_printable_strings(data: bytes, min_len: int = 5) -> list:
    """Extract printable ASCII strings from raw bytes (like `strings` utility)."""
    result = []
    current = []
    for byte in data:
        ch = chr(byte)
        if ch in string.printable and ch not in "\n\r\t":
            current.append(ch)
        else:
            if len(current) >= min_len:
                result.append("".join(current))
            current = []
    if len(current) >= min_len:
        result.append("".join(current))
    return result


def detect_file_type(file_path: Path) -> dict:
    """Detect true file type using python-magic or fallback."""
    ext = file_path.suffix.lower()
    result = {"extension": ext, "mime_type": "unknown", "description": "unknown"}

    if HAS_MAGIC:
        try:
            mime = magic.from_file(str(file_path), mime=True)
            desc = magic.from_file(str(file_path))
            result["mime_type"] = mime
            result["description"] = desc
        except Exception as e:
            log.warning(f"python-magic error: {e}")
    else:
        # Simple fallback based on magic bytes
        with open(file_path, "rb") as f:
            header = f.read(8)
        if header[:2] == b"MZ":
            result["mime_type"] = "application/x-dosexec"
            result["description"] = "PE32 executable (Windows)"
        elif header[:4] == b"PK\x03\x04":
            result["mime_type"] = "application/zip"
            result["description"] = "ZIP archive"
        elif header[:4] == b"%PDF":
            result["mime_type"] = "application/pdf"
            result["description"] = "PDF document"
        elif header[:2] in (b"\xff\xfe", b"\xfe\xff", b"\xef\xbb\xbf"):
            result["mime_type"] = "text/plain"
            result["description"] = "Unicode text"
        else:
            result["mime_type"] = f"application/octet-stream"
            result["description"] = f"Unknown binary (ext: {ext})"

    result["is_executable"] = result["mime_type"] in (
        "application/x-dosexec",
        "application/x-executable",
        "application/x-sharedlib",
    )
    result["is_archive"] = result["mime_type"] in (
        "application/zip",
        "application/x-tar",
        "application/x-rar",
        "application/x-7z-compressed",
    )
    return result


# ===========================================================================
# ZIP-specific analysis
# ===========================================================================

def analyze_zip(file_path: Path) -> dict:
    """Analyse a ZIP archive — list contents and flag suspicious members."""
    result = {
        "file_count": 0,
        "total_compressed_size": 0,
        "total_uncompressed_size": 0,
        "nested_exe_count": 0,
        "nested_script_count": 0,
        "suspicious_filenames": [],
        "entries": [],
    }
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            names = zf.namelist()
            result["file_count"] = len(names)
            for info in zf.infolist():
                entry = {
                    "name": info.filename,
                    "compressed_size": info.compress_size,
                    "uncompressed_size": info.file_size,
                    "compress_type": info.compress_type,
                }
                result["total_compressed_size"] += info.compress_size
                result["total_uncompressed_size"] += info.file_size
                lower = info.filename.lower()
                if lower.endswith(".exe") or lower.endswith(".dll"):
                    result["nested_exe_count"] += 1
                    result["suspicious_filenames"].append(info.filename)
                if lower.endswith((".bat", ".ps1", ".vbs", ".js", ".cmd", ".hta")):
                    result["nested_script_count"] += 1
                    result["suspicious_filenames"].append(info.filename)
                result["entries"].append(entry)
    except Exception as e:
        result["error"] = str(e)
    return result


# ===========================================================================
# PE (pefile) analysis
# ===========================================================================

def analyze_pe_pefile(file_path: Path) -> dict:
    """Full PE analysis using pefile library."""
    if not HAS_PEFILE:
        return {"error": "pefile not available"}

    result = {
        "is_valid_pe": False,
        "machine_type": None,
        "timestamp": None,
        "entry_point": None,
        "image_base": None,
        "subsystem": None,
        "dll_characteristics": [],
        "sections": [],
        "imports": {},
        "exports": [],
        "resources": [],
        "dangerous_imports": [],
        "suspicious_import_count": 0,
        "total_import_count": 0,
        "has_debug_info": False,
        "is_packed": False,
        "packer_indicators": [],
        "overall_entropy": 0.0,
    }

    try:
        pe = pefile.PE(str(file_path))
        result["is_valid_pe"] = True

        # ---- File header ----
        result["machine_type"] = pefile.MACHINE_TYPE.get(
            pe.FILE_HEADER.Machine, hex(pe.FILE_HEADER.Machine)
        )
        result["timestamp"] = pe.FILE_HEADER.TimeDateStamp
        result["entry_point"] = hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint)
        result["image_base"] = hex(pe.OPTIONAL_HEADER.ImageBase)
        result["subsystem"] = pefile.SUBSYSTEM_TYPE.get(
            pe.OPTIONAL_HEADER.Subsystem, str(pe.OPTIONAL_HEADER.Subsystem)
        )

        # ---- DLL characteristics ----
        dll_chars = pe.OPTIONAL_HEADER.DllCharacteristics
        char_flags = {
            0x0040: "DYNAMIC_BASE (ASLR)",
            0x0100: "NX_COMPAT (DEP)",
            0x0400: "NO_ISOLATION",
            0x0800: "NO_SEH",
            0x1000: "NO_BIND",
            0x4000: "GUARD_CF (Control Flow Guard)",
            0x8000: "TERMINAL_SERVER_AWARE",
        }
        result["dll_characteristics"] = [
            name for mask, name in char_flags.items() if dll_chars & mask
        ]

        # ---- Sections ----
        section_entropies = []
        for section in pe.sections:
            try:
                name = section.Name.rstrip(b"\x00").decode("utf-8", errors="replace")
            except Exception:
                name = repr(section.Name)
            data = section.get_data()
            entropy = compute_entropy(data)
            section_entropies.append(entropy)
            sec_info = {
                "name": name,
                "virtual_address": hex(section.VirtualAddress),
                "virtual_size": section.Misc_VirtualSize,
                "raw_size": section.SizeOfRawData,
                "entropy": entropy,
                "characteristics": hex(section.Characteristics),
                "is_executable": bool(section.Characteristics & 0x20000000),
                "is_writable": bool(section.Characteristics & 0x80000000),
                "is_readable": bool(section.Characteristics & 0x40000000),
            }
            # High entropy (>7.0) may indicate packing/encryption
            if entropy > 7.0:
                sec_info["high_entropy_warning"] = True
                result["packer_indicators"].append(f"Section '{name}' has high entropy: {entropy}")
            result["sections"].append(sec_info)

        result["overall_entropy"] = round(
            sum(section_entropies) / len(section_entropies), 4
        ) if section_entropies else 0.0

        # ---- Imports ----
        if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                dll_name = entry.dll.decode("utf-8", errors="replace").lower()
                funcs = []
                for imp in entry.imports:
                    func_name = imp.name.decode("utf-8", errors="replace") if imp.name else f"ord_{imp.ordinal}"
                    funcs.append(func_name)
                    result["total_import_count"] += 1

                    # Check against dangerous list
                    dll_key = dll_name
                    if dll_key in DANGEROUS_IMPORTS:
                        for dangerous_fn in DANGEROUS_IMPORTS[dll_key]:
                            if dangerous_fn.lower() in func_name.lower():
                                result["dangerous_imports"].append({
                                    "dll": dll_name,
                                    "function": func_name,
                                })
                                result["suspicious_import_count"] += 1
                                break
                result["imports"][dll_name] = funcs

        # ---- Exports ----
        if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
            for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                name = exp.name.decode("utf-8", errors="replace") if exp.name else f"ord_{exp.ordinal}"
                result["exports"].append(name)

        # ---- Resources ----
        if hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
            for res_type in pe.DIRECTORY_ENTRY_RESOURCE.entries:
                res_name = pefile.RESOURCE_TYPE.get(res_type.id, str(res_type.id))
                result["resources"].append(str(res_name))

        # ---- Debug info ----
        result["has_debug_info"] = hasattr(pe, "DIRECTORY_ENTRY_DEBUG")

        # ---- Packing detection heuristics ----
        if result["overall_entropy"] > 6.8:
            result["packer_indicators"].append(
                f"High overall entropy ({result['overall_entropy']}) — possible packing"
            )
        if len(result["sections"]) <= 2 and result["total_import_count"] < 5:
            result["packer_indicators"].append(
                "Very few sections and imports — typical packer stub"
            )
        # UPX signature
        section_names_lower = [s["name"].lower() for s in result["sections"]]
        if any("upx" in n for n in section_names_lower):
            result["packer_indicators"].append("UPX section names detected")
        if result["packer_indicators"]:
            result["is_packed"] = True

        pe.close()

    except pefile.PEFormatError as e:
        result["error"] = f"Not a valid PE file: {e}"
    except Exception as e:
        result["error"] = str(e)

    return result


# ===========================================================================
# LIEF deep analysis
# ===========================================================================

def analyze_lief(file_path: Path) -> dict:
    """Deep binary analysis using LIEF."""
    if not HAS_LIEF:
        return {"error": "lief not available"}

    result = {
        "format": "unknown",
        "is_pie": False,
        "has_nx": False,
        "has_stack_canary": False,
        "tls_callbacks": [],
        "relocations_count": 0,
        "signatures": [],
        "overlay_size": 0,
        "overlay_entropy": 0.0,
        "has_authenticode": False,
        "authenticode_valid": False,
    }

    try:
        binary = lief.parse(str(file_path))
        if binary is None:
            result["error"] = "LIEF could not parse this file"
            return result

        fmt = binary.format
        result["format"] = str(fmt).split(".")[-1]

        if isinstance(binary, lief.PE.Binary):
            result["is_pie"] = binary.is_pie
            result["has_nx"] = binary.has_nx
            result["relocations_count"] = len(list(binary.relocations))

            # TLS callbacks (often used for anti-analysis)
            if binary.has_tls:
                try:
                    cbs = list(binary.tls.callbacks)
                    result["tls_callbacks"] = [hex(cb) for cb in cbs]
                    if cbs:
                        result["tls_warning"] = "TLS callbacks detected — possible anti-debug"
                except Exception:
                    pass

            # Overlay (data appended after the last section)
            try:
                overlay = bytes(binary.overlay)
                result["overlay_size"] = len(overlay)
                if overlay:
                    result["overlay_entropy"] = compute_entropy(overlay)
                    if result["overlay_entropy"] > 6.5:
                        result["overlay_warning"] = "High-entropy overlay — may contain encrypted payload"
            except Exception:
                pass

            # Authenticode signature
            try:
                sigs = list(binary.signatures)
                result["has_authenticode"] = len(sigs) > 0
                for sig in sigs:
                    vr = sig.check()
                    result["authenticode_valid"] = (
                        vr == lief.PE.Signature.VERIFICATION_FLAGS.OK
                    )
                    result["signatures"].append({
                        "valid": result["authenticode_valid"],
                        "version": sig.version,
                    })
            except Exception:
                pass

    except Exception as e:
        result["error"] = str(e)

    return result


# ===========================================================================
# String analysis
# ===========================================================================

def analyze_strings(file_path: Path) -> dict:
    """Extract printable strings and flag suspicious patterns."""
    result = {
        "total_strings": 0,
        "suspicious_hits": [],
        "urls_found": [],
        "ips_found": [],
        "sample_strings": [],
    }

    with open(file_path, "rb") as f:
        data = f.read()

    strings = extract_printable_strings(data, min_len=5)
    result["total_strings"] = len(strings)
    result["sample_strings"] = strings[:200]  # keep first 200 for report

    seen_hits = set()
    for s in strings:
        s_lower = s.lower()
        for pattern in SUSPICIOUS_STRINGS:
            if pattern.lower() in s_lower and pattern not in seen_hits:
                result["suspicious_hits"].append({"pattern": pattern, "context": s[:120]})
                seen_hits.add(pattern)

        # Simple URL detection
        if s.startswith(("http://", "https://", "ftp://")):
            result["urls_found"].append(s[:200])

        # Simple IPv4 detection
        parts = s.split(".")
        if len(parts) == 4:
            try:
                if all(0 <= int(p) <= 255 for p in parts):
                    result["ips_found"].append(s)
            except ValueError:
                pass

    # Deduplicate
    result["urls_found"] = list(set(result["urls_found"]))[:50]
    result["ips_found"] = list(set(result["ips_found"]))[:50]
    return result


# ===========================================================================
# Risk scoring
# ===========================================================================

def compute_risk_score(features: dict) -> dict:
    """
    Heuristic risk score (0-100) based on static indicators.
    This is a pre-ML quick assessment.
    """
    score = 0
    reasons = []

    pe = features.get("pe_analysis", {})
    lief_data = features.get("lief_analysis", {})
    strings = features.get("string_analysis", {})
    file_info = features.get("file_info", {})
    file_type = features.get("file_type", {})

    # Packed / high entropy
    if pe.get("is_packed"):
        score += 20
        reasons.append("File appears packed or obfuscated (+20)")

    overall_entropy = pe.get("overall_entropy", 0)
    if overall_entropy > 7.2:
        score += 15
        reasons.append(f"Very high section entropy {overall_entropy} (+15)")
    elif overall_entropy > 6.5:
        score += 8
        reasons.append(f"Elevated section entropy {overall_entropy} (+8)")

    # Dangerous imports
    dangerous_count = pe.get("suspicious_import_count", 0)
    if dangerous_count >= 5:
        score += 20
        reasons.append(f"{dangerous_count} dangerous API imports (+20)")
    elif dangerous_count >= 2:
        score += 10
        reasons.append(f"{dangerous_count} dangerous API imports (+10)")

    # TLS callbacks (anti-debug)
    if lief_data.get("tls_callbacks"):
        score += 10
        reasons.append("TLS callbacks detected — anti-debug technique (+10)")

    # Overlay
    if lief_data.get("overlay_entropy", 0) > 6.5:
        score += 12
        reasons.append("High-entropy data overlay — hidden payload (+12)")

    # Suspicious strings
    hit_count = len(strings.get("suspicious_hits", []))
    if hit_count >= 10:
        score += 15
        reasons.append(f"{hit_count} suspicious string patterns (+15)")
    elif hit_count >= 5:
        score += 8
        reasons.append(f"{hit_count} suspicious string patterns (+8)")

    # URLs in binary
    url_count = len(strings.get("urls_found", []))
    if url_count > 0:
        score += min(url_count * 3, 10)
        reasons.append(f"{url_count} hardcoded URLs found (+{min(url_count * 3, 10)})")

    # Unsigned executable
    if file_type.get("is_executable") and not lief_data.get("has_authenticode"):
        score += 5
        reasons.append("Unsigned executable (+5)")

    # Nested executables in ZIP
    zip_data = features.get("zip_analysis", {})
    if zip_data.get("nested_exe_count", 0) > 0:
        score += 15
        reasons.append(f"ZIP contains {zip_data['nested_exe_count']} nested executable(s) (+15)")

    score = min(score, 100)

    risk_level = "CLEAN"
    if score >= 70:
        risk_level = "HIGH"
    elif score >= 40:
        risk_level = "MEDIUM"
    elif score >= 15:
        risk_level = "LOW"

    return {
        "score": score,
        "risk_level": risk_level,
        "reasons": reasons,
    }


# ===========================================================================
# Main analysis pipeline
# ===========================================================================

def analyze_file(file_path_str: str, output_dir: Path = RESULTS_DIR) -> dict:
    """
    Full static analysis pipeline.
    Returns the complete features dict and saves features.json.
    """
    file_path = Path(file_path_str).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    log.info(f"Starting static analysis of: {file_path.name} ({file_path.stat().st_size:,} bytes)")

    # ---- Basic file info ----
    stat = file_path.stat()
    file_info = {
        "filename": file_path.name,
        "filepath": str(file_path),
        "file_size_bytes": stat.st_size,
        "file_size_kb": round(stat.st_size / 1024, 2),
        "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "analysis_timestamp": datetime.now().isoformat(),
    }

    # ---- Hashes ----
    log.info("Computing file hashes...")
    hashes = compute_hashes(file_path)
    file_info.update(hashes)

    # ---- File type detection ----
    log.info("Detecting file type...")
    file_type = detect_file_type(file_path)
    log.info(f"Detected: {file_type['description']} (MIME: {file_type['mime_type']})")

    # ---- String analysis (always run) ----
    log.info("Extracting printable strings...")
    string_analysis = analyze_strings(file_path)
    log.info(f"Found {string_analysis['total_strings']} strings, "
             f"{len(string_analysis['suspicious_hits'])} suspicious hits")

    # ---- PE analysis ----
    pe_analysis = {}
    if file_type.get("is_executable") or file_path.suffix.lower() in (".exe", ".dll", ".sys"):
        log.info("Running PE analysis (pefile)...")
        pe_analysis = analyze_pe_pefile(file_path)
        if pe_analysis.get("is_valid_pe"):
            log.info(f"Valid PE — {len(pe_analysis.get('sections', []))} sections, "
                     f"{pe_analysis.get('total_import_count', 0)} imports, "
                     f"packed={pe_analysis.get('is_packed', False)}")
    else:
        log.info("Not an executable — skipping PE analysis")

    # ---- LIEF deep analysis ----
    lief_analysis = {}
    if file_type.get("is_executable") or file_path.suffix.lower() in (".exe", ".dll", ".sys"):
        log.info("Running deep binary analysis (LIEF)...")
        lief_analysis = analyze_lief(file_path)
    else:
        log.info("Not an executable — skipping LIEF analysis")

    # ---- ZIP analysis ----
    zip_analysis = {}
    if file_type.get("is_archive") or file_path.suffix.lower() == ".zip":
        log.info("Analyzing ZIP archive contents...")
        zip_analysis = analyze_zip(file_path)
        log.info(f"ZIP contains {zip_analysis.get('file_count', 0)} files, "
                 f"{zip_analysis.get('nested_exe_count', 0)} executables")

    # ---- Assemble full feature set ----
    features = {
        "schema_version": "1.0",
        "file_info": file_info,
        "file_type": file_type,
        "pe_analysis": pe_analysis,
        "lief_analysis": lief_analysis,
        "zip_analysis": zip_analysis,
        "string_analysis": string_analysis,
    }

    # ---- Risk scoring ----
    log.info("Computing heuristic risk score...")
    risk = compute_risk_score(features)
    features["heuristic_risk"] = risk
    log.info(f"Risk Score: {risk['score']}/100 — Level: {risk['risk_level']}")

    # ---- Save output ----
    output_path = output_dir / "features.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(features, f, indent=2, default=str)
    log.info(f"Features saved to: {output_path}")

    return features


# ===========================================================================
# CLI entry point
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="StealthOS Static Feature Extractor — Step 1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python static_analysis.py sample.exe
  python static_analysis.py malware.zip --output ./custom_results
  python static_analysis.py suspicious.exe --verbose
        """,
    )
    parser.add_argument("file", help="Path to EXE, DLL, or ZIP file to analyze")
    parser.add_argument(
        "--output", "-o",
        default=str(RESULTS_DIR),
        help="Output directory for features.json (default: ./results/)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        features = analyze_file(args.file, output_dir)

        # Print summary to terminal
        print("\n" + "=" * 60)
        print("  STEALTIOS — STATIC ANALYSIS COMPLETE")
        print("=" * 60)
        fi = features["file_info"]
        ft = features["file_type"]
        risk = features["heuristic_risk"]

        print(f"  File     : {fi['filename']}")
        print(f"  Size     : {fi['file_size_kb']} KB")
        print(f"  Type     : {ft['description']}")
        print(f"  MD5      : {fi['md5']}")
        print(f"  SHA256   : {fi['sha256']}")
        print(f"  Risk     : {risk['score']}/100  [{risk['risk_level']}]")

        if risk["reasons"]:
            print("\n  Risk Reasons:")
            for reason in risk["reasons"]:
                print(f"    • {reason}")

        pe = features.get("pe_analysis", {})
        if pe.get("is_valid_pe"):
            print(f"\n  PE Info:")
            print(f"    Sections : {len(pe.get('sections', []))}")
            print(f"    Imports  : {pe.get('total_import_count', 0)}")
            print(f"    Packed   : {pe.get('is_packed', False)}")
            print(f"    Entropy  : {pe.get('overall_entropy', 0)}")
            if pe.get("dangerous_imports"):
                print(f"    Dangerous APIs ({pe['suspicious_import_count']}):")
                for di in pe["dangerous_imports"][:10]:
                    print(f"      ↳ {di['dll']} → {di['function']}")

        strings = features.get("string_analysis", {})
        print(f"\n  Strings  : {strings.get('total_strings', 0)} total, "
              f"{len(strings.get('suspicious_hits', []))} suspicious")
        if strings.get("urls_found"):
            print(f"  URLs     : {strings['urls_found'][:3]}")

        output_path = output_dir / "features.json"
        print(f"\n  [OK] Output : {output_path}")
        print("=" * 60 + "\n")

        return 0

    except FileNotFoundError as e:
        log.error(str(e))
        return 1
    except Exception as e:
        log.error(f"Analysis failed: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
