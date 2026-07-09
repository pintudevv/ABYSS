"""
ABYSS — Forensic Logger (Step 6)
=====================================
Merges outputs from all pipeline stages into a single, structured
forensic report consumable by both humans and the Next.js frontend.

Input files  (results/ directory):
    features.json              — static analysis (Step 1)
    behavior.json              — sandbox dynamic analysis (Step 3)
    classification_result.json — ML classifier output (Step 4)
    deception_log.json         — deception layer events (Step 5)

Output files (results/ directory):
    forensic_report.json    — machine-readable full report
    forensic_summary.txt    — human-readable text summary

Usage:
    python forensic_logger.py
    python forensic_logger.py --results-dir /path/to/results
    python forensic_logger.py --analyst-id "analyst-007"
    python forensic_logger.py --no-pretty
"""

# ── stdlib ───────────────────────────────────────────────────────────────────
import argparse
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("forensic_logger")

# ── constants ────────────────────────────────────────────────────────────────
RESULTS_DIR = Path(__file__).parent / "results"

SRC_FEATURES       = "features.json"
SRC_BEHAVIOR       = "behavior.json"
SRC_CLASSIFICATION = "classification_result.json"
SRC_DECEPTION      = "deception_log.json"

OUT_REPORT  = "forensic_report.json"
OUT_SUMMARY = "forensic_summary.txt"

RISK_THRESHOLDS: List[Tuple[int, str]] = [
    (80, "CRITICAL"),
    (60, "HIGH"),
    (40, "MEDIUM"),
    (20, "LOW"),
    (0,  "INFO"),
]


# ── helpers ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_load_json(path: Path) -> Optional[Dict[str, Any]]:
    """
    Load JSON with full error isolation.
    Returns None on any failure — never raises.
    """
    if not path.exists():
        log.warning("Source file not found: %s — proceeding without it", path)
        return None
    if path.stat().st_size == 0:
        log.warning("Source file is empty: %s — proceeding without it", path)
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        log.error("JSON parse error in %s at line %d col %d — skipping",
                  path.name, exc.lineno, exc.colno)
        return None
    except OSError as exc:
        log.error("Cannot read %s: %s — skipping", path.name, exc)
        return None
    if not isinstance(data, dict):
        log.error("%s root must be a JSON object, got %s — skipping",
                  path.name, type(data).__name__)
        return None
    return data


def _safe_str(val: Any, default: str = "unknown") -> str:
    if val is None:
        return default
    s = str(val).strip()
    return s if s else default


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_bool(val: Any, default: bool = False) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes")
    if isinstance(val, (int, float)):
        return bool(val)
    return default


def _safe_list(val: Any) -> list:
    return val if isinstance(val, list) else []


def _safe_dict(val: Any) -> dict:
    return val if isinstance(val, dict) else {}


def _score_to_risk(score: int) -> str:
    for threshold, label in RISK_THRESHOLDS:
        if score >= threshold:
            return label
    return "INFO"


def _parse_timestamp(val: Any) -> Optional[str]:
    """
    Normalise any timestamp to ISO-8601 UTC string.
    Accepts: ISO-8601 strings, Unix epoch (int/float), None.
    Returns None if unparseable — never raises.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(val, tz=timezone.utc).isoformat()
        except (OSError, OverflowError, ValueError):
            return None
    if not isinstance(val, str):
        return None
    val = val.strip()
    if not val:
        return None
    val_clean = val.replace("Z", "+00:00")
    formats = [
        None,  # fromisoformat
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S.%f",
    ]
    for fmt in formats:
        try:
            if fmt is None:
                dt = datetime.fromisoformat(val_clean)
            else:
                dt = datetime.strptime(val, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue
    log.debug("Could not parse timestamp '%s' — storing as-is", val)
    return val


# ── source parsers ────────────────────────────────────────────────────────────

class FeaturesParser:
    """Parses results/features.json produced by static_analysis.py."""

    def __init__(self, data: Optional[Dict[str, Any]]) -> None:
        self._d: Dict[str, Any] = data or {}

    def filename(self) -> str:
        fi = _safe_dict(self._d.get("file_info"))
        return _safe_str(fi.get("filename"), "unknown")

    def filepath(self) -> str:
        fi = _safe_dict(self._d.get("file_info"))
        return _safe_str(fi.get("filepath"), "")

    def analysis_timestamp(self) -> Optional[str]:
        fi = _safe_dict(self._d.get("file_info"))
        return _parse_timestamp(fi.get("analysis_timestamp"))

    def hashes(self) -> Dict[str, str]:
        fi = _safe_dict(self._d.get("file_info"))
        return {
            "md5":    _safe_str(fi.get("md5"),    ""),
            "sha1":   _safe_str(fi.get("sha1"),   ""),
            "sha256": _safe_str(fi.get("sha256"), ""),
        }

    def file_size_bytes(self) -> int:
        fi = _safe_dict(self._d.get("file_info"))
        return _safe_int(fi.get("file_size_bytes"), 0)

    def risk_score(self) -> int:
        hr = _safe_dict(self._d.get("heuristic_risk"))
        return _safe_int(hr.get("score"), 0)

    def risk_level(self) -> str:
        hr = _safe_dict(self._d.get("heuristic_risk"))
        return _safe_str(hr.get("risk_level"), "UNKNOWN")

    def risk_reasons(self) -> List[str]:
        hr = _safe_dict(self._d.get("heuristic_risk"))
        return [_safe_str(r) for r in _safe_list(hr.get("reasons"))]

    def suspicious_imports(self) -> List[str]:
        pe = _safe_dict(self._d.get("pe_analysis"))
        return [_safe_str(i) for i in _safe_list(pe.get("dangerous_imports"))]

    def is_packed(self) -> bool:
        pe = _safe_dict(self._d.get("pe_analysis"))
        return _safe_bool(pe.get("is_packed"), False)

    def overall_entropy(self) -> float:
        pe = _safe_dict(self._d.get("pe_analysis"))
        return _safe_float(pe.get("overall_entropy"), 0.0)

    def urls_found(self) -> List[str]:
        sa = _safe_dict(self._d.get("string_analysis"))
        return [_safe_str(u) for u in _safe_list(sa.get("urls_found"))]

    def ips_found(self) -> List[str]:
        sa = _safe_dict(self._d.get("string_analysis"))
        return [_safe_str(ip) for ip in _safe_list(sa.get("ips_found"))]

    def suspicious_string_hits(self) -> List[Dict[str, str]]:
        sa = _safe_dict(self._d.get("string_analysis"))
        out = []
        for item in _safe_list(sa.get("suspicious_hits")):
            if isinstance(item, dict):
                out.append({
                    "pattern": _safe_str(item.get("pattern"), ""),
                    "context": _safe_str(item.get("context"), ""),
                })
        return out

    def has_authenticode(self) -> bool:
        la = _safe_dict(self._d.get("lief_analysis"))
        return _safe_bool(la.get("has_authenticode"), False)

    def authenticode_valid(self) -> bool:
        la = _safe_dict(self._d.get("lief_analysis"))
        return _safe_bool(la.get("authenticode_valid"), False)

    def overlay_warning(self) -> Optional[str]:
        la = _safe_dict(self._d.get("lief_analysis"))
        w = la.get("overlay_warning")
        return _safe_str(w) if w else None

    def timeline_events(self) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        ts = self.analysis_timestamp() or _now_iso()

        events.append({
            "timestamp":   ts,
            "event_type":  "static_analysis",
            "description": f"Static analysis started on '{self.filename()}'",
            "severity":    "INFO",
            "source":      "static_analysis",
        })

        if self.is_packed():
            events.append({
                "timestamp":   ts,
                "event_type":  "packing_detected",
                "description": "File appears packed — possible obfuscation/evasion",
                "severity":    "HIGH",
                "source":      "static_analysis",
            })

        ow = self.overlay_warning()
        if ow:
            events.append({
                "timestamp":   ts,
                "event_type":  "overlay_warning",
                "description": ow,
                "severity":    "MEDIUM",
                "source":      "static_analysis",
            })

        for imp in self.suspicious_imports():
            events.append({
                "timestamp":   ts,
                "event_type":  "suspicious_import",
                "description": f"Dangerous import detected: {imp}",
                "severity":    "HIGH",
                "source":      "static_analysis",
            })

        score = self.risk_score()
        if score > 0:
            events.append({
                "timestamp":   ts,
                "event_type":  "heuristic_risk",
                "description": f"Heuristic risk score: {score}/100 ({self.risk_level()})",
                "severity":    _score_to_risk(score),
                "source":      "static_analysis",
            })

        return events


class BehaviorParser:
    """Parses results/behavior.json produced by sandbox_runner.py (Cuckoo output)."""

    def __init__(self, data: Optional[Dict[str, Any]]) -> None:
        self._d: Dict[str, Any] = data or {}

    def processes(self) -> List[Dict[str, Any]]:
        out = []
        for proc in _safe_list(self._d.get("processes")):
            if not isinstance(proc, dict):
                continue
            out.append({
                "name":       _safe_str(proc.get("name", proc.get("process_name", "unknown")), "unknown"),
                "pid":        _safe_int(proc.get("pid"), 0),
                "parent":     _safe_str(proc.get("parent_process", proc.get("parent", "")), ""),
                "suspicious": _safe_bool(proc.get("suspicious"), False),
            })
        return out

    def network_connections(self) -> List[Dict[str, Any]]:
        net = _safe_dict(self._d.get("network", {}))
        out = []
        raw = net if isinstance(net, list) else _safe_list(net.get("connections", net.get("tcp", [])))
        for conn in raw:
            if not isinstance(conn, dict):
                continue
            out.append({
                "ip":           _safe_str(conn.get("dst_ip", conn.get("ip", "0.0.0.0")), "0.0.0.0"),
                "port":         _safe_int(conn.get("dst_port", conn.get("port", 0)), 0),
                "domain":       _safe_str(conn.get("domain", conn.get("hostname", "")), ""),
                "country_hint": _safe_str(conn.get("country", conn.get("country_hint", "")), ""),
                "protocol":     _safe_str(conn.get("protocol", "TCP"), "TCP"),
                "blocked":      _safe_bool(conn.get("blocked"), False),
                "sinkholed":    _safe_bool(conn.get("sinkholed"), False),
            })
        for dns in _safe_list(net.get("dns", [])):
            if not isinstance(dns, dict):
                continue
            answers = _safe_list(dns.get("answers", []))
            ip_from_dns = _safe_str(answers[0], "") if answers else ""
            out.append({
                "ip":           ip_from_dns,
                "port":         53,
                "domain":       _safe_str(dns.get("request", dns.get("domain", "")), ""),
                "country_hint": "",
                "protocol":     "DNS",
                "blocked":      _safe_bool(dns.get("blocked"), False),
                "sinkholed":    _safe_bool(dns.get("sinkholed"), False),
            })
        return out

    def file_accesses(self) -> List[Dict[str, Any]]:
        out = []
        for fa in _safe_list(self._d.get("files", [])):
            if not isinstance(fa, dict):
                continue
            out.append({
                "path":             _safe_str(fa.get("path", fa.get("filename", "")), ""),
                "was_honeypot":     _safe_bool(fa.get("was_honeypot"), False),
                "data_intercepted": _safe_bool(fa.get("data_intercepted"), False),
                "blocked":          _safe_bool(fa.get("blocked"), False),
            })
        return out

    def registry_ops(self) -> List[Dict[str, Any]]:
        out = []
        for reg in _safe_list(self._d.get("registry", [])):
            if not isinstance(reg, dict):
                continue
            out.append({
                "key":       _safe_str(reg.get("key", reg.get("regkey", "")), ""),
                "operation": _safe_str(reg.get("operation", reg.get("type", "READ")), "READ"),
                "blocked":   _safe_bool(reg.get("blocked"), False),
            })
        return out

    def api_calls(self) -> List[Dict[str, Any]]:
        out = []
        for call in _safe_list(self._d.get("api_calls", [])):
            if not isinstance(call, dict):
                continue
            out.append({
                "api":            _safe_str(call.get("api", call.get("name", "")), ""),
                "dll":            _safe_str(call.get("dll", call.get("module", "")), ""),
                "params_summary": _safe_str(call.get("params_summary", call.get("args_summary", "")), ""),
                "action":         _safe_str(call.get("action", ""), ""),
            })
        return out

    def start_time(self) -> Optional[str]:
        return _parse_timestamp(self._d.get("start_time"))

    def end_time(self) -> Optional[str]:
        return _parse_timestamp(self._d.get("end_time"))

    def duration_seconds(self) -> Optional[float]:
        v = self._d.get("analysis_duration_seconds")
        if v is not None:
            return _safe_float(v)
        st = self._d.get("start_time")
        et = self._d.get("end_time")
        if isinstance(st, str) and isinstance(et, str):
            try:
                s = datetime.fromisoformat(st.replace("Z", "+00:00"))
                e = datetime.fromisoformat(et.replace("Z", "+00:00"))
                return (e - s).total_seconds()
            except ValueError:
                pass
        return None

    def timeline_events(self) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        st = self.start_time() or _now_iso()

        if self.start_time():
            events.append({
                "timestamp":   st,
                "event_type":  "sandbox_start",
                "description": "Sandbox dynamic analysis session started",
                "severity":    "INFO",
                "source":      "sandbox",
            })

        for proc in self.processes():
            if proc["suspicious"]:
                events.append({
                    "timestamp":   st,
                    "event_type":  "suspicious_process",
                    "description": f"Suspicious process spawned: {proc['name']} (PID {proc['pid']})",
                    "severity":    "HIGH",
                    "source":      "sandbox",
                })

        for conn in self.network_connections():
            sev = "HIGH" if not conn["blocked"] else "MEDIUM"
            desc = f"Network connection attempt to {conn['ip']}:{conn['port']}"
            if conn["domain"]:
                desc += f" ({conn['domain']})"
            if conn["blocked"]:
                desc += " — BLOCKED"
            if conn["sinkholed"]:
                desc += " — SINKHOLED"
            events.append({
                "timestamp":   st,
                "event_type":  "network_connection",
                "description": desc,
                "severity":    sev,
                "source":      "sandbox",
            })

        for reg in self.registry_ops():
            events.append({
                "timestamp":   st,
                "event_type":  "registry_access",
                "description": f"Registry {reg['operation']} on {reg['key']}",
                "severity":    "MEDIUM" if not reg["blocked"] else "LOW",
                "source":      "sandbox",
            })

        if self.end_time():
            events.append({
                "timestamp":   self.end_time(),
                "event_type":  "sandbox_end",
                "description": "Sandbox dynamic analysis session ended",
                "severity":    "INFO",
                "source":      "sandbox",
            })

        return events


class ClassificationParser:
    """Parses results/classification_result.json produced by classifier.py."""

    def __init__(self, data: Optional[Dict[str, Any]]) -> None:
        self._d: Dict[str, Any] = data or {}

    def threat_detected(self) -> bool:
        pred = self._d.get("prediction", self._d.get("label"))
        if pred is None:
            return False
        if isinstance(pred, bool):
            return pred
        return _safe_str(pred).upper() not in ("BENIGN", "CLEAN", "SAFE", "0", "FALSE", "")

    def threat_type(self) -> str:
        return _safe_str(
            self._d.get("threat_type", self._d.get("malware_family", self._d.get("label"))),
            "UNKNOWN"
        )

    def confidence(self) -> float:
        raw = self._d.get("confidence", self._d.get("probability", self._d.get("score")))
        c = _safe_float(raw, -1.0)
        if c < 0:
            return 0.0
        return round(c / 100.0 if c > 1.0 else c, 4)

    def is_zero_day(self) -> bool:
        return _safe_bool(self._d.get("is_zero_day", self._d.get("zero_day")), False)

    def risk_score(self) -> int:
        return _safe_int(self._d.get("risk_score", self._d.get("heuristic_score")), 0)

    def model_votes(self) -> Dict[str, Any]:
        return _safe_dict(self._d.get("model_votes", {}))

    def analysis_timestamp(self) -> Optional[str]:
        return _parse_timestamp(self._d.get("analysis_timestamp", self._d.get("timestamp")))

    def recommendation(self) -> str:
        explicit = self._d.get("recommendation")
        if explicit:
            return _safe_str(explicit)
        if not self.threat_detected():
            return "File appears clean. No action required."
        if self.is_zero_day():
            return "QUARANTINE IMMEDIATELY — novel zero-day behaviour detected. Submit sample to threat intel."
        conf = self.confidence()
        if conf >= 0.85:
            return "QUARANTINE AND DELETE — high-confidence malware detection."
        if conf >= 0.60:
            return "QUARANTINE — likely malicious. Investigate before execution."
        return "REVIEW — uncertain classification. Manual analysis recommended."

    def timeline_events(self) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        ts = self.analysis_timestamp() or _now_iso()
        label = "MALWARE" if self.threat_detected() else "BENIGN"
        severity = "CRITICAL" if self.threat_detected() else "INFO"
        events.append({
            "timestamp":   ts,
            "event_type":  "ml_classification",
            "description": (
                f"ML classifier verdict: {label} "
                f"({self.threat_type()}, confidence {self.confidence():.1%})"
            ),
            "severity":    severity,
            "source":      "classifier",
        })
        if self.is_zero_day():
            events.append({
                "timestamp":   ts,
                "event_type":  "zero_day_detected",
                "description": "Zero-day / novel threat behaviour detected by autoencoder anomaly model",
                "severity":    "CRITICAL",
                "source":      "classifier",
            })
        return events


class DeceptionParser:
    """Parses results/deception_log.json produced by deception_layer.py."""

    def __init__(self, data: Optional[Dict[str, Any]]) -> None:
        self._d: Dict[str, Any] = data or {}

    def session_start(self) -> Optional[str]:
        return _parse_timestamp(self._d.get("session_start", self._d.get("start_time")))

    def session_end(self) -> Optional[str]:
        return _parse_timestamp(self._d.get("session_end", self._d.get("end_time")))

    def api_hooks(self) -> List[Dict[str, Any]]:
        out = []
        for hook in _safe_list(self._d.get("api_hooks", [])):
            if not isinstance(hook, dict):
                continue
            out.append({
                "api":            _safe_str(hook.get("api", hook.get("function", hook.get("name", ""))), ""),
                "dll":            _safe_str(hook.get("dll", hook.get("module", "")), ""),
                "params_summary": _safe_str(hook.get("params_summary", hook.get("args", "")), ""),
                "action":         _safe_str(hook.get("action", "INTERCEPTED"), "INTERCEPTED"),
            })
        return out

    def files_attempted(self) -> List[Dict[str, Any]]:
        out = []
        for fa in _safe_list(self._d.get("files_attempted", [])):
            if not isinstance(fa, dict):
                continue
            out.append({
                "path":             _safe_str(fa.get("path", fa.get("filename", "")), ""),
                "was_honeypot":     _safe_bool(fa.get("was_honeypot", fa.get("honeypot")), False),
                "data_intercepted": _safe_bool(fa.get("data_intercepted", fa.get("intercepted")), False),
                "blocked":          _safe_bool(fa.get("blocked"), False),
            })
        return out

    def data_intercepted(self) -> List[Dict[str, Any]]:
        out = []
        for di in _safe_list(self._d.get("data_intercepted", [])):
            if not isinstance(di, dict):
                continue
            out.append({
                "type":                _safe_str(di.get("type", di.get("data_type", "")), ""),
                "description":         _safe_str(di.get("description", ""), ""),
                "mock_data_returned":  _safe_bool(di.get("mock_data_returned", di.get("fake_data")), True),
                "real_data_protected": _safe_bool(di.get("real_data_protected"), True),
            })
        return out

    def ips_contacted(self) -> List[Dict[str, Any]]:
        out = []
        for entry in _safe_list(self._d.get("ips_contacted", [])):
            if not isinstance(entry, dict):
                continue
            out.append({
                "ip":           _safe_str(entry.get("ip", entry.get("dst_ip", "")), ""),
                "port":         _safe_int(entry.get("port", entry.get("dst_port", 0)), 0),
                "domain":       _safe_str(entry.get("domain", entry.get("hostname", "")), ""),
                "country_hint": _safe_str(entry.get("country_hint", entry.get("country", "")), ""),
                "protocol":     _safe_str(entry.get("protocol", "TCP"), "TCP"),
                "blocked":      _safe_bool(entry.get("blocked"), True),
                "sinkholed":    _safe_bool(entry.get("sinkholed"), True),
            })
        return out

    def registry_accessed(self) -> List[Dict[str, Any]]:
        out = []
        for reg in _safe_list(self._d.get("registry_accessed", [])):
            if not isinstance(reg, dict):
                continue
            out.append({
                "key":       _safe_str(reg.get("key", reg.get("regkey", "")), ""),
                "operation": _safe_str(reg.get("operation", reg.get("type", "READ")), "READ"),
                "blocked":   _safe_bool(reg.get("blocked"), False),
            })
        return out

    def mock_data_served(self) -> List[Dict[str, Any]]:
        out = []
        for md in _safe_list(self._d.get("mock_data_served", [])):
            if not isinstance(md, dict):
                continue
            out.append({
                "filename":        _safe_str(md.get("filename", md.get("file", "")), ""),
                "content_type":    _safe_str(md.get("content_type", md.get("type", "text/plain")), "text/plain"),
                "times_requested": _safe_int(md.get("times_requested", md.get("count", 1)), 1),
            })
        return out

    def timeline_events(self) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        ss = self.session_start() or _now_iso()
        se = self.session_end()

        if self.session_start():
            events.append({
                "timestamp":   ss,
                "event_type":  "deception_session_start",
                "description": "Deception layer activated — API hooks and honeypots armed",
                "severity":    "INFO",
                "source":      "deception",
            })

        for hook in self.api_hooks():
            ts = _parse_timestamp(hook.get("timestamp", ss)) or ss
            events.append({
                "timestamp":   ts,
                "event_type":  "api_hook_triggered",
                "description": f"API hook triggered: {hook['dll']}.{hook['api']} -> {hook['action']}",
                "severity":    "HIGH",
                "source":      "deception",
            })

        for fa in self.files_attempted():
            ts = _parse_timestamp(fa.get("timestamp", ss)) or ss
            desc = f"File access attempt: {fa['path']}"
            sev = "CRITICAL" if fa["was_honeypot"] else "MEDIUM"
            if fa["was_honeypot"]:
                desc += " — HONEYPOT triggered"
            if fa["blocked"]:
                desc += " — BLOCKED"
            events.append({
                "timestamp":   ts,
                "event_type":  "file_access_attempt",
                "description": desc,
                "severity":    sev,
                "source":      "deception",
            })

        for di in self.data_intercepted():
            ts = _parse_timestamp(di.get("timestamp", ss)) or ss
            events.append({
                "timestamp":   ts,
                "event_type":  "data_interception",
                "description": f"Data theft attempt intercepted: {di['type']} — {di['description']}",
                "severity":    "CRITICAL",
                "source":      "deception",
            })

        for ip_entry in self.ips_contacted():
            ts = _parse_timestamp(ip_entry.get("timestamp", ss)) or ss
            desc = f"C2 connection attempt to {ip_entry['ip']}:{ip_entry['port']}"
            if ip_entry["domain"]:
                desc += f" ({ip_entry['domain']})"
            if ip_entry["sinkholed"]:
                desc += " — SINKHOLED"
            elif ip_entry["blocked"]:
                desc += " — BLOCKED"
            events.append({
                "timestamp":   ts,
                "event_type":  "c2_contact_attempt",
                "description": desc,
                "severity":    "CRITICAL",
                "source":      "deception",
            })

        if se:
            events.append({
                "timestamp":   se,
                "event_type":  "deception_session_end",
                "description": "Deception layer session closed",
                "severity":    "INFO",
                "source":      "deception",
            })

        return events


# ── report builder ────────────────────────────────────────────────────────────

class ForensicReportBuilder:
    """
    Merges parsed data from all four pipeline stages into a comprehensive
    forensic_report.json.

    Weaponized-autism guarantees:
      1. Every field has a hardcoded default — report is always structurally complete.
      2. No field is ever None in the final JSON output.
      3. Timeline is merged across all sources and sorted chronologically.
      4. Counts (blocked/allowed/mock) are DERIVED from data, not taken from
         potentially stale summary fields.
      5. Field names match what the Next.js ThreatReport component expects.
    """

    def __init__(
        self,
        features:       Optional[Dict[str, Any]],
        behavior:       Optional[Dict[str, Any]],
        classification: Optional[Dict[str, Any]],
        deception:      Optional[Dict[str, Any]],
        analyst_id:     str,
        build_start:    datetime,
    ) -> None:
        self._fp  = FeaturesParser(features)
        self._bp  = BehaviorParser(behavior)
        self._cp  = ClassificationParser(classification)
        self._dp  = DeceptionParser(deception)
        self._analyst_id  = analyst_id
        self._build_start = build_start
        self._sources_available = {
            "features":       features is not None,
            "behavior":       behavior is not None,
            "classification": classification is not None,
            "deception":      deception is not None,
        }

    # ── private merge helpers ─────────────────────────────────────────────────

    def _merge_files_attempted(self) -> List[Dict[str, Any]]:
        """Merge + deduplicate file accesses from sandbox & deception by path."""
        seen: Dict[str, Dict[str, Any]] = {}
        for fa in self._bp.file_accesses():
            key = fa["path"].lower().strip()
            if key:
                seen[key] = fa
        # Deception layer entries are authoritative — overwrite sandbox entries
        for fa in self._dp.files_attempted():
            key = fa["path"].lower().strip()
            if key:
                seen[key] = fa
        return list(seen.values())

    def _merge_ips_contacted(self) -> List[Dict[str, Any]]:
        """Merge + deduplicate network contacts by (ip, port)."""
        seen: Dict[Tuple[str, int], Dict[str, Any]] = {}
        for conn in self._bp.network_connections():
            if conn["ip"] not in ("", "0.0.0.0"):
                seen[(conn["ip"], conn["port"])] = conn
        # Deception layer is authoritative
        for conn in self._dp.ips_contacted():
            if conn["ip"] not in ("", "0.0.0.0"):
                seen[(conn["ip"], conn["port"])] = conn
        return list(seen.values())

    def _merge_registry(self) -> List[Dict[str, Any]]:
        """Merge + deduplicate registry ops by (key, operation)."""
        seen: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for reg in self._bp.registry_ops():
            seen[(reg["key"].lower(), reg["operation"].upper())] = reg
        for reg in self._dp.registry_accessed():
            seen[(reg["key"].lower(), reg["operation"].upper())] = reg
        return list(seen.values())

    def _merge_api_hooks(self) -> List[Dict[str, Any]]:
        """Merge + deduplicate API hooks by (dll, api). Deception entries win."""
        seen: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for call in self._bp.api_calls():
            seen[(call["dll"].lower(), call["api"].lower())] = call
        for hook in self._dp.api_hooks():
            seen[(hook["dll"].lower(), hook["api"].lower())] = hook
        return list(seen.values())

    def _build_timeline(self) -> List[Dict[str, Any]]:
        """
        Collect events from all four parsers, normalise, sort chronologically.
        Events without a parseable timestamp are placed at the END of the
        timeline (never dropped) — zero data loss.
        """
        raw_events: List[Dict[str, Any]] = (
            self._fp.timeline_events() +
            self._bp.timeline_events() +
            self._cp.timeline_events() +
            self._dp.timeline_events()
        )
        fallback_ts = _now_iso()
        normalised: List[Dict[str, Any]] = []

        for ev in raw_events:
            if not isinstance(ev, dict):
                continue
            ts = _parse_timestamp(ev.get("timestamp")) or fallback_ts
            normalised.append({
                "timestamp":   ts,
                "event_type":  _safe_str(ev.get("event_type"), "event"),
                "description": _safe_str(ev.get("description"), ""),
                "severity":    _safe_str(ev.get("severity"), "INFO"),
                "source":      _safe_str(ev.get("source"), "unknown"),
            })

        normalised.sort(key=lambda e: e["timestamp"])
        for idx, ev in enumerate(normalised, start=1):
            ev["seq"] = idx
        return normalised

    def _compute_risk_level(self) -> str:
        if self._sources_available["classification"] and self._cp.threat_detected():
            conf = self._cp.confidence()
            if conf >= 0.85:
                return "CRITICAL"
            if conf >= 0.65:
                return "HIGH"
            if conf >= 0.45:
                return "MEDIUM"
            return "LOW"
        if self._sources_available["features"]:
            return _score_to_risk(self._fp.risk_score())
        return "LOW"

    def _derive_recommendation(self) -> str:
        if self._sources_available["classification"]:
            return self._cp.recommendation()
        if self._sources_available["features"]:
            score = self._fp.risk_score()
            if score >= 70:
                return "QUARANTINE — high heuristic risk score."
            if score >= 40:
                return "REVIEW — elevated heuristic indicators. Manual inspection recommended."
        return "No sufficient data for a recommendation. Re-run with all pipeline stages."

    def _count_blocked(
        self,
        files: List[Dict[str, Any]],
        ips:   List[Dict[str, Any]],
        registry: List[Dict[str, Any]],
    ) -> int:
        count = 0
        for f in files:
            if _safe_bool(f.get("blocked")):
                count += 1
        for ip in ips:
            if _safe_bool(ip.get("blocked")) or _safe_bool(ip.get("sinkholed")):
                count += 1
        for reg in registry:
            if _safe_bool(reg.get("blocked")):
                count += 1
        for hook in self._dp.api_hooks():
            if _safe_str(hook.get("action"), "").upper() in (
                "BLOCKED", "INTERCEPTED", "FAKED", "SPOOFED"
            ):
                count += 1
        return count

    def _count_allowed(
        self,
        files: List[Dict[str, Any]],
        ips:   List[Dict[str, Any]],
        registry: List[Dict[str, Any]],
    ) -> int:
        count = 0
        for f in files:
            if not _safe_bool(f.get("blocked")):
                count += 1
        for ip in ips:
            if not _safe_bool(ip.get("blocked")) and not _safe_bool(ip.get("sinkholed")):
                count += 1
        for reg in registry:
            if not _safe_bool(reg.get("blocked")):
                count += 1
        return count

    # ── public build ──────────────────────────────────────────────────────────

    def build(self) -> Dict[str, Any]:
        """
        Build and return the complete forensic report dict.
        Every field is guaranteed present and non-None.
        """
        build_end      = datetime.now(timezone.utc)
        total_duration = round((build_end - self._build_start).total_seconds(), 3)

        files_attempted   = self._merge_files_attempted()
        ips_contacted     = self._merge_ips_contacted()
        registry_accessed = self._merge_registry()
        api_hooks         = self._merge_api_hooks()
        mock_data_served  = self._dp.mock_data_served()
        data_intercepted  = self._dp.data_intercepted()
        processes_spawned = self._bp.processes()
        timeline          = self._build_timeline()

        total_blocked        = self._count_blocked(files_attempted, ips_contacted, registry_accessed)
        total_allowed        = self._count_allowed(files_attempted, ips_contacted, registry_accessed)
        total_mock_responses = sum(
            _safe_int(m.get("times_requested"), 0) for m in mock_data_served
        )

        threat_detected = (
            self._cp.threat_detected()
            if self._sources_available["classification"]
            else self._fp.risk_score() >= 50
        )
        threat_type = (
            self._cp.threat_type()
            if self._sources_available["classification"]
            else ("SUSPICIOUS" if threat_detected else "NONE")
        )
        confidence = (
            self._cp.confidence()
            if self._sources_available["classification"]
            else round(self._fp.risk_score() / 100.0, 4)
        )
        is_zero_day = (
            self._cp.is_zero_day()
            if self._sources_available["classification"]
            else False
        )

        missing_sources = [k for k, v in self._sources_available.items() if not v]
        data_completeness = (
            "COMPLETE"
            if not missing_sources
            else f"PARTIAL — missing: {', '.join(missing_sources)}"
        )

        report: Dict[str, Any] = {
            # ── metadata ─────────────────────────────────────────────────────
            "metadata": {
                "filename":               self._fp.filename(),
                "filepath":               self._fp.filepath(),
                "file_size_bytes":        self._fp.file_size_bytes(),
                "hashes":                 self._fp.hashes(),
                "analysis_time":          build_end.isoformat(),
                "total_duration_seconds": total_duration,
                "analyst_id":             self._analyst_id,
                "report_id":              str(uuid.uuid4()),
                "schema_version":         "2.0",
                "data_completeness":      data_completeness,
                "sources_loaded":         {k: v for k, v in self._sources_available.items()},
            },

            # ── executive_summary ─────────────────────────────────────────────
            "executive_summary": {
                "threat_detected":      threat_detected,
                "threat_type":          threat_type,
                "confidence":           confidence,
                "risk_level":           self._compute_risk_level(),
                "is_zero_day":          is_zero_day,
                "recommendation":       self._derive_recommendation(),
                "static_risk_score":    self._fp.risk_score(),
                "static_risk_level":    self._fp.risk_level(),
                "static_risk_reasons":  self._fp.risk_reasons(),
                "is_packed":            self._fp.is_packed(),
                "overall_entropy":      self._fp.overall_entropy(),
                "has_authenticode":     self._fp.has_authenticode(),
                "authenticode_valid":   self._fp.authenticode_valid(),
                "model_votes":          self._cp.model_votes(),
            },

            # ── deception artefacts ───────────────────────────────────────────
            "files_attempted":     files_attempted,
            "data_intercepted":    data_intercepted,
            "ips_contacted":       ips_contacted,
            "registry_accessed":   registry_accessed,
            "processes_spawned":   processes_spawned,
            "api_hooks_triggered": api_hooks,
            "mock_data_served":    mock_data_served,

            # ── static artefacts ──────────────────────────────────────────────
            "urls_found":             self._fp.urls_found(),
            "ips_found_in_strings":   self._fp.ips_found(),
            "suspicious_string_hits": self._fp.suspicious_string_hits(),
            "suspicious_imports":     self._fp.suspicious_imports(),

            # ── timeline ──────────────────────────────────────────────────────
            "timeline": timeline,

            # ── aggregate metrics ─────────────────────────────────────────────
            "total_blocked":        total_blocked,
            "total_allowed":        total_allowed,
            "total_mock_responses": total_mock_responses,
            "total_events":         len(timeline),
            "total_processes":      len(processes_spawned),
            "total_network_hits":   len(ips_contacted),
            "total_registry_hits":  len(registry_accessed),
            "total_file_hits":      len(files_attempted),
            "total_api_hooks":      len(api_hooks),
        }

        return report


# ── text summary generator ────────────────────────────────────────────────────

def generate_text_summary(report: Dict[str, Any]) -> str:
    """
    Render the report as a human-readable forensic summary.
    Every section is independently guarded — never raises.
    """
    lines: List[str] = []

    def section(title: str) -> None:
        lines.append("")
        lines.append("=" * 72)
        lines.append(f"  {title}")
        lines.append("=" * 72)

    def field(label: str, value: Any) -> None:
        lines.append(f"  {label:<28} {value}")

    def bullet(text: str) -> None:
        lines.append(f"    * {text}")

    # header
    lines.append("+" + "=" * 70 + "+")
    lines.append("|         ABYSS -- Forensic Analysis Report" + " " * 23 + "|")
    lines.append("+" + "=" * 70 + "+")

    meta = _safe_dict(report.get("metadata"))
    lines.append(f"  Report ID    : {_safe_str(meta.get('report_id'), 'N/A')}")
    lines.append(f"  Generated    : {_safe_str(meta.get('analysis_time'), 'N/A')}")
    lines.append(f"  Analyst      : {_safe_str(meta.get('analyst_id'), 'N/A')}")
    lines.append(f"  Completeness : {_safe_str(meta.get('data_completeness'), 'UNKNOWN')}")

    # executive summary
    section("EXECUTIVE SUMMARY")
    es              = _safe_dict(report.get("executive_summary"))
    threat_detected = _safe_bool(es.get("threat_detected"))
    risk_level      = _safe_str(es.get("risk_level"), "UNKNOWN")
    verdict_banner  = "!!! MALWARE DETECTED !!!" if threat_detected else "<<< FILE APPEARS CLEAN >>>"

    lines.append("")
    lines.append(f"  VERDICT  : {verdict_banner}")
    lines.append(f"  RISK     : {risk_level}")
    lines.append("")

    field("Threat Type:",          _safe_str(es.get("threat_type"), "NONE"))
    field("Confidence:",           f"{_safe_float(es.get('confidence'), 0.0):.1%}")
    field("Zero-Day:",             "YES !!!" if _safe_bool(es.get("is_zero_day")) else "No")
    field("Static Risk Score:",    f"{_safe_int(es.get('static_risk_score'), 0)} / 100")
    field("Static Risk Level:",    _safe_str(es.get("static_risk_level"), "UNKNOWN"))
    field("Is Packed:",            "YES" if _safe_bool(es.get("is_packed")) else "No")
    field("Overall Entropy:",      f"{_safe_float(es.get('overall_entropy'), 0.0):.4f}")
    field("Has Authenticode:",     "Yes" if _safe_bool(es.get("has_authenticode")) else "No")
    field("Authenticode Valid:",   "Yes" if _safe_bool(es.get("authenticode_valid")) else "No")
    lines.append("")
    lines.append(f"  Recommendation:")
    lines.append(f"    >> {_safe_str(es.get('recommendation'), 'N/A')}")

    static_reasons = _safe_list(es.get("static_risk_reasons"))
    if static_reasons:
        lines.append("")
        lines.append("  Heuristic Risk Reasons:")
        for r in static_reasons:
            bullet(str(r))

    # file metadata
    section("FILE METADATA")
    hashes = _safe_dict(meta.get("hashes"))
    field("Filename:",   _safe_str(meta.get("filename"), "unknown"))
    field("Filepath:",   _safe_str(meta.get("filepath"), "N/A"))
    field("Size:",       f"{_safe_int(meta.get('file_size_bytes'), 0):,} bytes")
    field("MD5:",        _safe_str(hashes.get("md5"),    "N/A"))
    field("SHA1:",       _safe_str(hashes.get("sha1"),   "N/A"))
    field("SHA256:",     _safe_str(hashes.get("sha256"), "N/A"))
    field("Duration:",   f"{_safe_float(meta.get('total_duration_seconds'), 0):.3f}s")

    # aggregate stats
    section("AGGREGATE STATISTICS")
    field("Events in Timeline:",    _safe_int(report.get("total_events"), 0))
    field("Total Blocked:",         _safe_int(report.get("total_blocked"), 0))
    field("Total Allowed:",         _safe_int(report.get("total_allowed"), 0))
    field("Mock Responses Served:", _safe_int(report.get("total_mock_responses"), 0))
    field("Processes Spawned:",     _safe_int(report.get("total_processes"), 0))
    field("Network Contacts:",      _safe_int(report.get("total_network_hits"), 0))
    field("Registry Hits:",         _safe_int(report.get("total_registry_hits"), 0))
    field("File Access Attempts:",  _safe_int(report.get("total_file_hits"), 0))
    field("API Hooks Triggered:",   _safe_int(report.get("total_api_hooks"), 0))

    # files attempted
    files = _safe_list(report.get("files_attempted"))
    if files:
        section(f"FILES ATTEMPTED ({len(files)})")
        for fa in files:
            flags = ""
            if _safe_bool(fa.get("was_honeypot")):
                flags += " [HONEYPOT]"
            if _safe_bool(fa.get("blocked")):
                flags += " [BLOCKED]"
            if _safe_bool(fa.get("data_intercepted")):
                flags += " [INTERCEPTED]"
            bullet(f"{_safe_str(fa.get('path'), 'unknown')}{flags}")

    # data intercepted
    data_int = _safe_list(report.get("data_intercepted"))
    if data_int:
        section(f"DATA THEFT ATTEMPTS ({len(data_int)})")
        for di in data_int:
            protected = (
                "Real data protected"
                if _safe_bool(di.get("real_data_protected"), True)
                else "REAL DATA AT RISK"
            )
            bullet(
                f"[{_safe_str(di.get('type'), 'UNKNOWN')}] "
                f"{_safe_str(di.get('description'), '')} -- "
                f"mock returned: {'Yes' if _safe_bool(di.get('mock_data_returned'), True) else 'No'} | "
                f"{protected}"
            )

    # IPs contacted
    ips = _safe_list(report.get("ips_contacted"))
    if ips:
        section(f"NETWORK CONTACTS ({len(ips)})")
        for ip in ips:
            if _safe_bool(ip.get("sinkholed")):
                status = "SINKHOLED"
            elif _safe_bool(ip.get("blocked")):
                status = "BLOCKED"
            else:
                status = "ALLOWED"
            domain_str = f" ({_safe_str(ip.get('domain'))})" if ip.get("domain") else ""
            bullet(
                f"{_safe_str(ip.get('ip'), '?')}:{_safe_int(ip.get('port'))} "
                f"{domain_str}[{_safe_str(ip.get('protocol'), 'TCP')}] -- {status}"
            )

    # registry
    registry = _safe_list(report.get("registry_accessed"))
    if registry:
        section(f"REGISTRY ACCESSES ({len(registry)})")
        for reg in registry:
            blocked_str = " [BLOCKED]" if _safe_bool(reg.get("blocked")) else ""
            bullet(
                f"{_safe_str(reg.get('operation'), 'READ')} "
                f"-> {_safe_str(reg.get('key'), 'unknown')}{blocked_str}"
            )

    # processes
    procs = _safe_list(report.get("processes_spawned"))
    if procs:
        section(f"PROCESSES SPAWNED ({len(procs)})")
        for p in procs:
            flag   = " !! SUSPICIOUS" if _safe_bool(p.get("suspicious")) else ""
            parent = f" <- {p['parent']}" if p.get("parent") else ""
            bullet(
                f"{_safe_str(p.get('name'), 'unknown')} "
                f"(PID {_safe_int(p.get('pid'))}){parent}{flag}"
            )

    # API hooks
    hooks = _safe_list(report.get("api_hooks_triggered"))
    if hooks:
        section(f"API HOOKS TRIGGERED ({len(hooks)})")
        for h in hooks:
            dll_api = f"{_safe_str(h.get('dll'), '?')}.{_safe_str(h.get('api'), '?')}"
            action  = _safe_str(h.get("action"), "INTERCEPTED")
            params  = _safe_str(h.get("params_summary"), "")
            detail  = f" -- {params}" if params else ""
            bullet(f"{dll_api} -> {action}{detail}")

    # mock data served
    mock = _safe_list(report.get("mock_data_served"))
    if mock:
        section(f"MOCK DATA SERVED ({len(mock)})")
        for m in mock:
            bullet(
                f"{_safe_str(m.get('filename'), 'unknown')} "
                f"[{_safe_str(m.get('content_type'), 'text/plain')}] "
                f"x{_safe_int(m.get('times_requested'), 0)} request(s)"
            )

    # suspicious imports
    sus_imp = _safe_list(report.get("suspicious_imports"))
    if sus_imp:
        section(f"DANGEROUS IMPORTS ({len(sus_imp)})")
        for imp in sus_imp:
            bullet(str(imp))

    # URLs found in binary
    urls = _safe_list(report.get("urls_found"))
    if urls:
        section(f"URLS FOUND IN BINARY ({len(urls)})")
        for u in urls:
            bullet(str(u))

    # timeline
    tl = _safe_list(report.get("timeline"))
    if tl:
        section(f"ATTACK TIMELINE ({len(tl)} events)")
        lines.append("")
        sev_tags = {
            "CRITICAL": "[CRIT]",
            "HIGH":     "[HIGH]",
            "MEDIUM":   "[MED ]",
            "LOW":      "[LOW ]",
            "INFO":     "[INFO]",
        }
        for ev in tl:
            seq     = _safe_int(ev.get("seq"), 0)
            ts      = _safe_str(ev.get("timestamp"), "?")[:19].replace("T", " ")
            sev     = _safe_str(ev.get("severity"), "INFO")
            ev_type = _safe_str(ev.get("event_type"), "event")
            desc    = _safe_str(ev.get("description"), "")
            source  = _safe_str(ev.get("source"), "?")
            tag     = sev_tags.get(sev, "[    ]")
            lines.append(f"  [{seq:>3}] {ts}  {tag} {sev:<8}  [{source}]")
            lines.append(f"        {ev_type}  ->  {desc}")
            lines.append("")

    # footer
    lines.append("=" * 72)
    lines.append("  END OF FORENSIC REPORT")
    lines.append("  Generated by ABYSS Forensic Logger v2.0")
    lines.append(f"  Report ID: {_safe_str(meta.get('report_id'), 'N/A')}")
    lines.append("=" * 72)
    lines.append("")

    return "\n".join(lines)


# ── I/O helpers ───────────────────────────────────────────────────────────────

def write_json(data: Dict[str, Any], path: Path, pretty: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    indent = 2 if pretty else None
    try:
        with path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=indent, ensure_ascii=False, default=str)
        log.info("Wrote JSON report  -> %s  (%s bytes)", path, path.stat().st_size)
    except OSError as exc:
        log.error("Failed to write %s: %s", path, exc)
        raise


def write_text(content: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("w", encoding="utf-8") as fh:
            fh.write(content)
        log.info("Wrote text summary -> %s  (%s bytes)", path, path.stat().st_size)
    except OSError as exc:
        log.error("Failed to write %s: %s", path, exc)
        raise


# ── main orchestrator ─────────────────────────────────────────────────────────

def run(results_dir: Path, analyst_id: str, pretty_json: bool) -> int:
    """
    Main orchestration function.

    Returns:
        0  -- success, all sources present
        1  -- partial failure (missing sources, but report written)
        2  -- fatal failure (cannot write output or zero sources loaded)
    """
    build_start = datetime.now(timezone.utc)
    log.info("ABYSS Forensic Logger v2.0 -- starting")
    log.info("Results directory: %s", results_dir.resolve())

    if not results_dir.exists():
        log.error("Results directory does not exist: %s", results_dir)
        return 2

    # load all source files
    features       = _safe_load_json(results_dir / SRC_FEATURES)
    behavior       = _safe_load_json(results_dir / SRC_BEHAVIOR)
    classification = _safe_load_json(results_dir / SRC_CLASSIFICATION)
    deception      = _safe_load_json(results_dir / SRC_DECEPTION)

    sources_loaded = sum(
        1 for s in [features, behavior, classification, deception]
        if s is not None
    )
    log.info("%d / 4 source files loaded successfully", sources_loaded)

    if sources_loaded == 0:
        log.error(
            "No source files could be loaded. "
            "Ensure at least one pipeline stage has run and written to: %s",
            results_dir
        )
        return 2

    # build report
    builder = ForensicReportBuilder(
        features=features,
        behavior=behavior,
        classification=classification,
        deception=deception,
        analyst_id=analyst_id,
        build_start=build_start,
    )

    try:
        report = builder.build()
    except Exception as exc:
        log.exception("Unexpected error during report build: %s", exc)
        return 2

    # write outputs
    report_path  = results_dir / OUT_REPORT
    summary_path = results_dir / OUT_SUMMARY
    exit_code    = 0

    try:
        write_json(report, report_path, pretty=pretty_json)
    except OSError:
        log.error("FATAL: Could not write forensic_report.json")
        return 2

    try:
        summary_text = generate_text_summary(report)
        write_text(summary_text, summary_path)
    except Exception as exc:
        log.warning(
            "Text summary generation failed: %s -- JSON report is still valid", exc
        )
        exit_code = 1

    if sources_loaded < 4:
        log.warning(
            "Report is PARTIAL -- %d source file(s) missing. "
            "Run the full pipeline for a complete report.",
            4 - sources_loaded,
        )
        exit_code = 1

    # console print
    es      = _safe_dict(report.get("executive_summary"))
    verdict = "MALWARE DETECTED" if _safe_bool(es.get("threat_detected")) else "Clean"
    risk    = _safe_str(es.get("risk_level"), "UNKNOWN")

    print("\n" + "-" * 60)
    print(f"  ABYSS Forensic Report -- {verdict}")
    print(f"  Risk Level    : {risk}")
    print(f"  Threat Type   : {_safe_str(es.get('threat_type'), 'N/A')}")
    print(f"  Confidence    : {_safe_float(es.get('confidence'), 0.0):.1%}")
    print(f"  Timeline      : {_safe_int(report.get('total_events'), 0)} events")
    print(f"  Blocked       : {_safe_int(report.get('total_blocked'), 0)} actions")
    print(f"  Report        : {report_path.resolve()}")
    print(f"  Summary       : {summary_path.resolve()}")
    print("-" * 60 + "\n")

    return exit_code


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forensic_logger",
        description="ABYSS Step 6 -- Forensic Report Builder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python forensic_logger.py
  python forensic_logger.py --results-dir ./results
  python forensic_logger.py --analyst-id analyst-007
  python forensic_logger.py --no-pretty
        """,
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=RESULTS_DIR,
        help=f"Directory containing pipeline result JSONs (default: {RESULTS_DIR})",
    )
    parser.add_argument(
        "--analyst-id",
        type=str,
        default="auto",
        help="Analyst identifier to embed in report (default: auto-generated UUID)",
    )
    parser.add_argument(
        "--no-pretty",
        action="store_true",
        default=False,
        help="Disable pretty-printing -- produces compact JSON",
    )
    return parser


def main() -> None:
    parser     = _build_arg_parser()
    args       = parser.parse_args()
    analyst_id = args.analyst_id
    if analyst_id == "auto":
        analyst_id = f"stealth-{uuid.uuid4().hex[:8]}"

    exit_code = run(
        results_dir=args.results_dir,
        analyst_id=analyst_id,
        pretty_json=not args.no_pretty,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
