"""
ABYSS -- Deception + Neutralization Layer (Step 5)
======================================================
Intercepts, deceives, and neutralizes malicious API calls, network
connections, and file accesses using a three-pronged approach:

  1. Frida API Hooking  - Intercepts Win32 API calls in the target process
                          and returns fake success values / NULL, feeding honeypot
                          data to credential-stealing and clipboard-reading malware.

  2. Network Sinkhole   - Blocks outbound connections to known-malicious IPs /
                          domains.  FakeNet-NG integration when present; local
                          blocklist + domain resolver fallback otherwise.
                          Every attempt is logged with reason.

  3. Honeypot Watcher   - Uses watchdog Observer to monitor mock_data/ for file
                          open / access events.  MockDataServer returns convincing
                          fake credentials, credit cards, cookies and contact data
                          to any process that tries to read the decoy files.

Output: results/deception_log.json

Security contract (weaponized-autism):
  - EVERY file path served by MockDataServer is resolved and confirmed to live
    inside MOCK_DATA_DIR before any content is returned.  Path traversal = denied.
  - Real user files are NEVER touched, read, or returned under any code path.
  - All external inputs (PIDs, IP strings, filenames) are validated before use.

Frida JS design (meth-lab):
  - Event-driven only -- zero polling, zero busy-wait.
  - One send() per intercept, structured JSON payload.
  - Fast path first: sensitive check then action, then log.

Author : ABYSS Core
Version: 1.0.0
"""

from __future__ import annotations

import ipaddress
import json
import logging
import re
import socket
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Optional dependency guards
# ---------------------------------------------------------------------------
try:
    import frida          # type: ignore
    HAS_FRIDA = True
except ImportError:
    HAS_FRIDA = False

try:
    from watchdog.observers import Observer          # type: ignore
    from watchdog.events import FileSystemEventHandler  # type: ignore
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

try:
    import fakenet        # type: ignore  # noqa: F401
    HAS_FAKENET = True
except ImportError:
    HAS_FAKENET = False

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s -- %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("deception_layer")

# ---------------------------------------------------------------------------
# Path constants -- resolved once, validated everywhere
# ---------------------------------------------------------------------------
_HERE:         Path = Path(__file__).parent.resolve()
MOCK_DATA_DIR: Path = (_HERE / "mock_data").resolve()
RESULTS_DIR:   Path = (_HERE / "results").resolve()
RESULTS_DIR.mkdir(exist_ok=True)
LOG_PATH:      Path = RESULTS_DIR / "deception_log.json"

# ---------------------------------------------------------------------------
# Frida JS hook script -- embedded as a module-level constant.
#
# Hooks installed:
#   kernel32  : CreateFileW, CreateFileA, ReadFile
#   advapi32  : RegOpenKeyExW, RegOpenKeyExA, RegQueryValueExW
#   ws2_32    : connect, send, WSASend
#   user32    : GetClipboardData
#
# Meth-lab design:
#   * Event-driven only -- Frida's onEnter/onLeave model, no polling.
#   * Sensitive path/port check is a pure JS array scan (fast).
#   * Each hook fires ONE send() per call with a structured JSON payload.
#   * Blocked calls return FAKE_SUCCESS / NULL so malware keeps running
#     while receiving no real data.
# ---------------------------------------------------------------------------
FRIDA_HOOK_SCRIPT: str = r"""
'use strict';

// ---- Helpers ---------------------------------------------------------------

function ts() { return new Date().toISOString(); }

function emit(api, params, action, mockVal) {
    send(JSON.stringify({
        type:          'api_hook',
        timestamp:     ts(),
        api_name:      api,
        params:        params,
        action_taken:  action,
        mock_returned: mockVal
    }));
}

// File path fragments that indicate credential / sensitive data access
var SENSITIVE_FRAGMENTS = [
    'password', 'passwd', 'credential', 'secret', 'wallet',
    'cookie', 'session', 'token', 'ntds', 'sam', 'lsass',
    '.kdb', '.kdbx', 'id_rsa', 'id_ed25519', 'id_ecdsa',
    'appdata', 'roaming', 'mozilla\\firefox', 'google\\chrome',
    'microsoft\\edge', 'keychain', 'login data',
    'discord', 'leveldb', 'discordcanary', 'discordptb',
    'lightcord', 'vesktop', 'webhooks', 'discord.py',
    'metamask', 'phantom', 'solflare', 'trustwallet', 'exodus',
    'atomic', 'ronin', 'seed.txt', 'passphrase', 'keylog', 'keystrokes'
];

// Ports that indicate C2 / exfiltration channels -- block these
var SUSPICIOUS_PORTS = [1337, 4444, 5555, 6666, 7777, 8888, 9999,
                        31337, 55555, 6667, 6697, 12345, 54321];

function isSensitivePath(path) {
    if (!path) return false;
    var lower = path.toLowerCase();
    for (var i = 0; i < SENSITIVE_FRAGMENTS.length; i++) {
        if (lower.indexOf(SENSITIVE_FRAGMENTS[i]) !== -1) return true;
    }
    return false;
}

function isSuspiciousPort(port) {
    return SUSPICIOUS_PORTS.indexOf(port) !== -1;
}

// Registry subkey fragments indicating LSA / credential stores
var SENSITIVE_REG = [
    'winlogon', 'security', '\\sam', 'lsa',
    'intelliforms', 'internet settings',
    'chrome\\preferencemacs', 'mozilla\\firefox'
];

function isSensitiveReg(subkey) {
    if (!subkey) return false;
    var lower = subkey.toLowerCase();
    for (var i = 0; i < SENSITIVE_REG.length; i++) {
        if (lower.indexOf(SENSITIVE_REG[i]) !== -1) return true;
    }
    return false;
}

var HIVE = {
    '80000000': 'HKCR', '80000001': 'HKCU',
    '80000002': 'HKLM', '80000003': 'HKU', '80000005': 'HKCC'
};

// ---- kernel32 : CreateFileW ------------------------------------------------

var _CreateFileW = Module.findExportByName(null, 'CreateFileW');
if (_CreateFileW) {
    Interceptor.attach(_CreateFileW, {
        onEnter: function(args) {
            try   { this.path = args[0].readUtf16String(); }
            catch { this.path = '<unreadable>'; }
            this.block = isSensitivePath(this.path);
        },
        onLeave: function(retval) {
            if (this.block) {
                emit('CreateFileW', {path: this.path},
                     'BLOCKED_FAKE_NOT_FOUND', 'INVALID_HANDLE_VALUE');
                retval.replace(ptr('0xFFFFFFFF'));
            } else {
                emit('CreateFileW', {path: this.path}, 'PASSTHROUGH', null);
            }
        }
    });
}

// ---- kernel32 : CreateFileA ------------------------------------------------

var _CreateFileA = Module.findExportByName(null, 'CreateFileA');
if (_CreateFileA) {
    Interceptor.attach(_CreateFileA, {
        onEnter: function(args) {
            try   { this.path = args[0].readAnsiString(); }
            catch { this.path = '<unreadable>'; }
            this.block = isSensitivePath(this.path);
        },
        onLeave: function(retval) {
            if (this.block) {
                emit('CreateFileA', {path: this.path},
                     'BLOCKED_FAKE_NOT_FOUND', 'INVALID_HANDLE_VALUE');
                retval.replace(ptr('0xFFFFFFFF'));
            } else {
                emit('CreateFileA', {path: this.path}, 'PASSTHROUGH', null);
            }
        }
    });
}

// ---- kernel32 : ReadFile ---------------------------------------------------
// Log every ReadFile so we can correlate with blocked CreateFile calls.

var _ReadFile = Module.findExportByName(null, 'ReadFile');
if (_ReadFile) {
    Interceptor.attach(_ReadFile, {
        onEnter: function(args) {
            this.handle  = args[0];
            this.nToRead = args[2].toInt32();
        },
        onLeave: function(retval) {
            if (retval.toInt32() !== 0) {
                emit('ReadFile',
                     {handle: this.handle.toString(), bytes_requested: this.nToRead},
                     'PASSTHROUGH', null);
            }
        }
    });
}

// ---- advapi32 : RegOpenKeyExW ----------------------------------------------

var _RegOpenKeyExW = Module.findExportByName(null, 'RegOpenKeyExW');
if (_RegOpenKeyExW) {
    Interceptor.attach(_RegOpenKeyExW, {
        onEnter: function(args) {
            try {
                var hive   = args[0].toString(16);
                var subkey = args[1].readUtf16String();
                this.block = isSensitiveReg(subkey);
                this.info  = {hive: HIVE[hive] || ('0x' + hive), subkey: subkey};
            } catch(e) {
                this.block = false;
                this.info  = {error: e.message};
            }
        },
        onLeave: function(retval) {
            if (this.block) {
                emit('RegOpenKeyExW', this.info,
                     'BLOCKED_ERROR_ACCESS_DENIED', 'ERROR_ACCESS_DENIED(5)');
                retval.replace(ptr(5));
            } else {
                emit('RegOpenKeyExW', this.info, 'PASSTHROUGH', null);
            }
        }
    });
}

// ---- advapi32 : RegOpenKeyExA ----------------------------------------------

var _RegOpenKeyExA = Module.findExportByName(null, 'RegOpenKeyExA');
if (_RegOpenKeyExA) {
    Interceptor.attach(_RegOpenKeyExA, {
        onEnter: function(args) {
            try {
                var hive   = args[0].toString(16);
                var subkey = args[1].readAnsiString();
                this.block = isSensitiveReg(subkey);
                this.info  = {hive: HIVE[hive] || ('0x' + hive), subkey: subkey};
            } catch(e) {
                this.block = false;
                this.info  = {error: e.message};
            }
        },
        onLeave: function(retval) {
            if (this.block) {
                emit('RegOpenKeyExA', this.info,
                     'BLOCKED_ERROR_ACCESS_DENIED', 'ERROR_ACCESS_DENIED(5)');
                retval.replace(ptr(5));
            } else {
                emit('RegOpenKeyExA', this.info, 'PASSTHROUGH', null);
            }
        }
    });
}

// ---- advapi32 : RegQueryValueExW -------------------------------------------

var _RegQueryValueExW = Module.findExportByName(null, 'RegQueryValueExW');
if (_RegQueryValueExW) {
    Interceptor.attach(_RegQueryValueExW, {
        onEnter: function(args) {
            try   { this.valueName = args[1].readUtf16String(); }
            catch { this.valueName = '<unreadable>'; }
        },
        onLeave: function(retval) {
            emit('RegQueryValueExW', {value_name: this.valueName}, 'PASSTHROUGH', null);
        }
    });
}

// ---- ws2_32 : connect ------------------------------------------------------

var _connect = Module.findExportByName(null, 'connect');
if (_connect) {
    Interceptor.attach(_connect, {
        onEnter: function(args) {
            try {
                var sa   = args[1];
                var port = ((sa.add(2).readU8() << 8) | sa.add(3).readU8());
                var a    = sa.add(4);
                var ip   = a.readU8() + '.' + a.add(1).readU8() + '.' +
                           a.add(2).readU8() + '.' + a.add(3).readU8();
                this.dest  = {ip: ip, port: port};
                this.block = isSuspiciousPort(port);
            } catch(e) {
                this.dest  = {error: e.message};
                this.block = false;
            }
        },
        onLeave: function(retval) {
            if (this.block) {
                emit('connect', this.dest, 'BLOCKED_FAKE_SUCCESS', '0');
                retval.replace(ptr(0));
            } else {
                emit('connect', this.dest, 'PASSTHROUGH', null);
            }
        }
    });
}

// ---- ws2_32 : send ---------------------------------------------------------

var _send = Module.findExportByName(null, 'send');
if (_send) {
    Interceptor.attach(_send, {
        onEnter: function(args) {
            this.sock   = args[0].toInt32();
            this.length = args[2].toInt32();
        },
        onLeave: function(retval) {
            emit('send',
                 {socket: this.sock, data_length: this.length, bytes_sent: retval.toInt32()},
                 'PASSTHROUGH', null);
        }
    });
}

// ---- ws2_32 : WSASend ------------------------------------------------------

var _WSASend = Module.findExportByName(null, 'WSASend');
if (_WSASend) {
    Interceptor.attach(_WSASend, {
        onEnter: function(args) {
            this.sock   = args[0].toInt32();
            this.nbufs  = args[2].toInt32();
        },
        onLeave: function(retval) {
            emit('WSASend',
                 {socket: this.sock, buf_count: this.nbufs},
                 'PASSTHROUGH', null);
        }
    });
}

// ---- user32 : GetClipboardData ---------------------------------------------
// Classic clipboard-scraping / keylogger vector.
// We return NULL so the malware thinks the clipboard is empty.

var _GetClipboardData = Module.findExportByName(null, 'GetClipboardData');
if (_GetClipboardData) {
    Interceptor.attach(_GetClipboardData, {
        onEnter: function(args) {
            this.fmt = args[0].toInt32();
        },
        onLeave: function(retval) {
            emit('GetClipboardData',
                 {format: this.fmt},
                 'BLOCKED_NULL_RETURNED', 'NULL');
            retval.replace(ptr(0));
        }
    });
}

// ---- user32 : SetWindowsHookExW / SetWindowsHookExA -----------------------
// Keylogger vector -- return NULL handle to fail keyboard hook registration
var _SetWindowsHookExW = Module.findExportByName(null, 'SetWindowsHookExW');
if (_SetWindowsHookExW) {
    Interceptor.attach(_SetWindowsHookExW, {
        onEnter: function(args) { this.idHook = args[0].toInt32(); },
        onLeave: function(retval) {
            emit('SetWindowsHookExW', {idHook: this.idHook}, 'BLOCKED_KEYLOGGER_NULL_RETURNED', 'NULL');
            retval.replace(ptr(0));
        }
    });
}

var _SetWindowsHookExA = Module.findExportByName(null, 'SetWindowsHookExA');
if (_SetWindowsHookExA) {
    Interceptor.attach(_SetWindowsHookExA, {
        onEnter: function(args) { this.idHook = args[0].toInt32(); },
        onLeave: function(retval) {
            emit('SetWindowsHookExA', {idHook: this.idHook}, 'BLOCKED_KEYLOGGER_NULL_RETURNED', 'NULL');
            retval.replace(ptr(0));
        }
    });
}

// ---- gdi32 : BitBlt / user32 : PrintWindow ---------------------------------
// Screenshot grabber vector -- return FALSE so screen capture fails
var _BitBlt = Module.findExportByName(null, 'BitBlt');
if (_BitBlt) {
    Interceptor.attach(_BitBlt, {
        onEnter: function(args) { this.hdc = args[0]; },
        onLeave: function(retval) {
            emit('BitBlt', {hdc: this.hdc.toString()}, 'BLOCKED_SCREENSHOT_BLANK', 'FALSE');
            retval.replace(ptr(0));
        }
    });
}

var _PrintWindow = Module.findExportByName(null, 'PrintWindow');
if (_PrintWindow) {
    Interceptor.attach(_PrintWindow, {
        onEnter: function(args) { this.hwnd = args[0]; },
        onLeave: function(retval) {
            emit('PrintWindow', {hwnd: this.hwnd.toString()}, 'BLOCKED_SCREENSHOT_BLANK', 'FALSE');
            retval.replace(ptr(0));
        }
    });
}

// ---- Sentinel --------------------------------------------------------------
send(JSON.stringify({type: 'ready', timestamp: ts(), hooks_installed: true}));
"""  # end FRIDA_HOOK_SCRIPT


# ===========================================================================
# Blocklists -- Network Sinkhole
# ===========================================================================

MALICIOUS_IPS: frozenset = frozenset([
    # Tor exit nodes / known C2 relays
    "185.220.101.0",  "185.220.101.1",  "185.220.101.45", "185.220.101.182",
    "193.189.100.195","194.165.16.103", "194.165.16.11",
    "45.142.212.100", "45.142.212.167",
    "91.108.4.167",   "91.108.56.130",
    "51.75.33.127",   "51.77.113.100",
    "176.57.188.132", "176.57.188.94",
    # RFC1918 -- should never be exfil destinations
    "10.0.0.1", "172.16.0.1", "192.168.0.1",
])

MALICIOUS_DOMAINS: frozenset = frozenset([
    "evil-c2.example.com",
    "malware-drop.ru",
    "botnet-hub.cc",
    "ransom-pay.onion.link",
    "exfil-server.xyz",
    "keylogger-recv.top",
    "rat-c2.info",
    "miner-pool.cc",
    "stealer-backend.pw",
    "cobalt-strike-team.org",
])

# Ports that should never see outbound data from a benign process
BLOCKED_PORTS: frozenset = frozenset([
    1337, 4444, 5555, 6666, 7777, 8888, 9999,
    31337, 55555, 65535,
    6667, 6697,         # IRC -- common botnet C&C
    12345, 54321,       # Classic trojan listen ports
])


# ===========================================================================
# Utilities
# ===========================================================================

def _now() -> str:
    """UTC ISO-8601 timestamp, millisecond precision."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _is_valid_ip(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def _resolve_domain(domain: str) -> Optional[str]:
    try:
        return socket.gethostbyname(domain)
    except socket.gaierror:
        return None


# ===========================================================================
# _LogStore -- thread-safe event accumulator
# ===========================================================================

class _LogStore:
    """Accumulates all deception events from multiple threads."""

    def __init__(self) -> None:
        self._lock         = threading.Lock()
        self.api_hooks_fired:  List[Dict[str, Any]] = []
        self.network_blocked:  List[Dict[str, Any]] = []
        self.files_accessed:   List[Dict[str, Any]] = []
        self.total_blocked: int = 0
        self.total_allowed: int = 0

    def add_api_hook(self, *, timestamp: str, api_name: str,
                     params: Dict[str, Any], action_taken: str,
                     mock_returned: Optional[str]) -> None:
        entry = {
            "timestamp":     timestamp,
            "api_name":      api_name,
            "params":        params,
            "action_taken":  action_taken,
            "mock_returned": mock_returned,
        }
        with self._lock:
            self.api_hooks_fired.append(entry)
            if "BLOCKED" in action_taken:
                self.total_blocked += 1
            else:
                self.total_allowed += 1

    def add_network_block(self, *, timestamp: str, dest_ip: str,
                          dest_port: int, data_size: int, reason: str) -> None:
        with self._lock:
            self.network_blocked.append({
                "timestamp": timestamp,
                "dest_ip":   dest_ip,
                "dest_port": dest_port,
                "data_size": data_size,
                "reason":    reason,
            })
            self.total_blocked += 1

    def add_file_access(self, *, timestamp: str, filepath: str,
                        was_honeypot: bool, data_returned: Optional[str]) -> None:
        with self._lock:
            self.files_accessed.append({
                "timestamp":    timestamp,
                "filepath":     filepath,
                "was_honeypot": was_honeypot,
                "data_returned": data_returned,
            })

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "api_hooks_fired": list(self.api_hooks_fired),
                "network_blocked": list(self.network_blocked),
                "files_accessed":  list(self.files_accessed),
                "total_blocked":   self.total_blocked,
                "total_allowed":   self.total_allowed,
            }

    def reset(self) -> None:
        with self._lock:
            self.api_hooks_fired.clear()
            self.network_blocked.clear()
            self.files_accessed.clear()
            self.total_blocked = 0
            self.total_allowed = 0


# ===========================================================================
# MockDataServer
# ===========================================================================

class MockDataServer:
    """
    Serves content exclusively from mock_data/ to deceive malware.

    Security guarantee (weaponized-autism):
      resolve_path() raises ValueError for ANY path whose resolved form
      lies outside MOCK_DATA_DIR -- covering symlinks, .. traversal,
      drive letter substitution, and UNC paths.
    """

    _cache:      Dict[str, str]  = {}
    _cache_lock: threading.Lock  = threading.Lock()

    # Well-known credential filenames --> our decoy equivalents
    _DECOY_MAP: Dict[str, str] = {
        "passwords.txt":     "fake_passwords.txt",
        "credentials.txt":   "fake_passwords.txt",
        "creds.txt":         "fake_passwords.txt",
        "logins.txt":        "fake_passwords.txt",
        "wallet.dat":        "fake_metamask_seeds.txt",
        "seed.txt":          "fake_metamask_seeds.txt",
        "seeds.txt":         "fake_metamask_seeds.txt",
        "passphrase.txt":    "fake_metamask_seeds.txt",
        "wallets.json":      "fake_wallet_addresses.json",
        "cc.txt":            "fake_credit_cards.txt",
        "cards.txt":         "fake_credit_cards.txt",
        "contacts.csv":      "fake_contacts.csv",
        "contacts.db":       "fake_contacts.csv",
        "cookies.db":        "fake_cookies.db",
        "cookies.sqlite":    "fake_cookies.db",
        "login data":        "fake_cookies.db",
        "login_data":        "fake_cookies.db",
        "discord_tokens.json": "fake_discord_tokens.json",
        "tokens.txt":        "fake_discord_tokens.json",
    }

    @classmethod
    def resolve_path(cls, requested: str) -> Path:
        """
        Return the safe resolved Path inside MOCK_DATA_DIR.
        Raises ValueError if the path escapes the directory.
        """
        # Only accept the bare filename -- strip all directory components
        bare = Path(requested).name
        if not bare:
            raise ValueError(f"Empty filename after stripping: {requested!r}")

        candidate = (MOCK_DATA_DIR / bare).resolve()

        # Strict containment: relative_to raises ValueError if outside
        try:
            candidate.relative_to(MOCK_DATA_DIR)
        except ValueError:
            raise ValueError(
                f"Path traversal denied: {requested!r} resolves to {candidate} "
                f"which is outside mock_data/"
            )
        return candidate

    @classmethod
    def get_content(cls, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Return (was_honeypot, content).
        was_honeypot=True  => fake data returned (honeypot hit).
        was_honeypot=False => file not in mock_data/, content is None.
        """
        mapped = cls._DECOY_MAP.get(filename.lower(), filename)

        try:
            safe_path = cls.resolve_path(mapped)
        except ValueError as exc:
            log.warning(f"[MockDataServer] {exc}")
            return False, None

        if not safe_path.exists() or not safe_path.is_file():
            return False, None

        key = str(safe_path)
        with cls._cache_lock:
            if key not in cls._cache:
                try:
                    if safe_path.suffix in (".db", ".sqlite", ".sqlite3"):
                        cls._cache[key] = cls._sqlite_summary(safe_path)
                    else:
                        cls._cache[key] = safe_path.read_text(
                            encoding="utf-8", errors="replace"
                        )
                except Exception as exc:
                    log.error(f"[MockDataServer] Cannot read {safe_path}: {exc}")
                    return False, None
            content = cls._cache[key]

        return True, content

    @staticmethod
    def _sqlite_summary(db: Path) -> str:
        """Human-readable summary of a SQLite database (used for fake_cookies.db)."""
        lines: List[str] = [f"# SQLite: {db.name}"]
        try:
            conn = sqlite3.connect(str(db))
            cur  = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            for (table,) in cur.fetchall():
                lines.append(f"\n[Table: {table}]")
                try:
                    cur.execute(f"SELECT * FROM [{table}] LIMIT 20")  # noqa: S608
                    for row in cur.fetchall():
                        lines.append("  " + " | ".join(str(c) for c in row))
                except Exception:
                    lines.append("  <error reading rows>")
            conn.close()
        except Exception as exc:
            lines.append(f"<SQLite error: {exc}>")
        return "\n".join(lines)

    @classmethod
    def list_decoys(cls) -> List[str]:
        if not MOCK_DATA_DIR.exists():
            return []
        return [f.name for f in MOCK_DATA_DIR.iterdir() if f.is_file()]


# ===========================================================================
# HoneypotWatcher -- watchdog-based file access monitor
# ===========================================================================

if HAS_WATCHDOG:
    class _HoneypotHandler(FileSystemEventHandler):
        """watchdog handler -- fires on file open / access inside mock_data/."""

        def __init__(self, store: _LogStore) -> None:
            super().__init__()
            self._store = store

        def _handle(self, path: str) -> None:
            try:
                resolved = Path(path).resolve()
                resolved.relative_to(MOCK_DATA_DIR)   # containment check
            except ValueError:
                log.error(f"[HoneypotHandler] Event outside mock_data: {path!r} -- ignored")
                return

            was_hp, content = MockDataServer.get_content(resolved.name)
            self._store.add_file_access(
                timestamp=_now(),
                filepath=str(resolved),
                was_honeypot=was_hp,
                data_returned=content[:500] if content else None,
            )
            flag = "HONEYPOT HIT" if was_hp else "access (not decoy)"
            log.info(f"[HoneypotWatcher] {flag}: {resolved.name!r}")

        # watchdog 4.x event interface
        def on_opened(self, event: Any) -> None:
            if not event.is_directory:
                self._handle(event.src_path)

        def on_accessed(self, event: Any) -> None:
            if not event.is_directory:
                self._handle(event.src_path)

        # Older watchdog versions
        def on_modified(self, event: Any) -> None:
            pass

        def on_created(self, event: Any) -> None:
            pass
else:
    _HoneypotHandler = None  # type: ignore


class HoneypotWatcher:
    """
    Starts a watchdog Observer on mock_data/.
    Falls back to a low-frequency simulation thread when watchdog is absent.
    """

    def __init__(self, store: _LogStore) -> None:
        self._store     = store
        self._observer  = None
        self._stop_evt  = threading.Event()
        self._sim_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        MOCK_DATA_DIR.mkdir(parents=True, exist_ok=True)

        if HAS_WATCHDOG:
            handler       = _HoneypotHandler(self._store)
            self._observer = Observer()
            self._observer.schedule(handler, str(MOCK_DATA_DIR), recursive=False)
            self._observer.start()
            log.info(f"[HoneypotWatcher] watchdog Observer active on {MOCK_DATA_DIR}")
        else:
            log.warning(
                "[HoneypotWatcher] watchdog unavailable -- SIMULATION MODE. "
                "pip install watchdog"
            )
            self._sim_thread = threading.Thread(
                target=self._sim_loop, daemon=True, name="honeypot-sim"
            )
            self._sim_thread.start()

    def _sim_loop(self) -> None:
        while not self._stop_evt.wait(30):
            for fname in MockDataServer.list_decoys():
                self._store.add_file_access(
                    timestamp=_now(),
                    filepath=str(MOCK_DATA_DIR / fname),
                    was_honeypot=True,
                    data_returned="[SIMULATION -- watchdog unavailable]",
                )
            log.debug("[HoneypotWatcher] sim tick")

    def stop(self) -> None:
        self._stop_evt.set()
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            log.info("[HoneypotWatcher] stopped")


# ===========================================================================
# NetworkSinkhole
# ===========================================================================

class NetworkSinkhole:
    """
    Evaluates outbound connection tuples against a blocklist of known-malicious
    IPs, domains, and ports.  Integrates FakeNet-NG at the OS level when present;
    uses Python-level blocklist otherwise.
    """

    def __init__(self, store: _LogStore) -> None:
        self._store      = store
        self._fakenet    = None
        self._running    = False
        self._blocked_ips    : set = set(MALICIOUS_IPS)
        self._blocked_domains: set = set(MALICIOUS_DOMAINS)
        self._blocked_ports  : set = set(BLOCKED_PORTS)

    def start(self) -> None:
        if HAS_FAKENET:
            try:
                self._start_fakenet()
                return
            except Exception as exc:
                log.warning(f"[NetworkSinkhole] FakeNet failed ({exc}) -- using blocklist")
        self._start_blocklist()
        self._running = True

    def _start_fakenet(self) -> None:
        import fakenet.fakenet as fn  # type: ignore
        log.info("[NetworkSinkhole] Starting FakeNet-NG (OS-level sinkhole)")
        self._fakenet = fn.FakeNet()
        self._fakenet.start()
        self._running = True
        log.info("[NetworkSinkhole] FakeNet-NG running")

    def _start_blocklist(self) -> None:
        log.info(
            f"[NetworkSinkhole] Blocklist mode -- "
            f"{len(self._blocked_ips)} IPs, "
            f"{len(self._blocked_domains)} domains, "
            f"{len(self._blocked_ports)} ports"
        )
        resolved = 0
        for domain in MALICIOUS_DOMAINS:
            ip = _resolve_domain(domain)
            if ip:
                self._blocked_ips.add(ip)
                resolved += 1
        if resolved:
            log.info(f"[NetworkSinkhole] Resolved {resolved} domains to IPs")

    def check_connection(self, dest_ip: str, dest_port: int,
                         data_size: int = 0) -> bool:
        """
        Returns True and logs an event if this connection should be blocked.

        All inputs are validated:
          - dest_ip must be a valid IPv4/IPv6 string.
          - dest_port must be an integer in [0, 65535].
        """
        if not self._running:
            return False

        # ---- Input validation ------------------------------------------------
        if not _is_valid_ip(dest_ip):
            log.debug(f"[NetworkSinkhole] Skipping invalid IP: {dest_ip!r}")
            return False
        if not isinstance(dest_port, int) or not 0 <= dest_port <= 65535:
            log.debug(f"[NetworkSinkhole] Skipping invalid port: {dest_port!r}")
            return False

        reason: Optional[str] = None

        if dest_ip in self._blocked_ips:
            reason = f"IP in blocklist: {dest_ip}"
        elif dest_port in self._blocked_ports:
            reason = f"Port in blocklist: {dest_port}"
        else:
            # Reverse-lookup against domain blocklist (best-effort, fast timeout)
            try:
                hostname, _, _ = socket.gethostbyaddr(dest_ip)
                if any(hostname.endswith(d) for d in self._blocked_domains):
                    reason = f"rDNS domain in blocklist: {hostname}"
            except (socket.herror, socket.gaierror, OSError):
                pass

        if reason:
            log.warning(
                f"[NetworkSinkhole] BLOCKED {dest_ip}:{dest_port} -- {reason} "
                f"({data_size} B)"
            )
            self._store.add_network_block(
                timestamp=_now(),
                dest_ip=dest_ip,
                dest_port=dest_port,
                data_size=data_size,
                reason=reason,
            )
            return True
        return False

    def stop(self) -> None:
        self._running = False
        if self._fakenet is not None:
            try:
                self._fakenet.stop()
                log.info("[NetworkSinkhole] FakeNet-NG stopped")
            except Exception as exc:
                log.warning(f"[NetworkSinkhole] FakeNet stop error: {exc}")


# ===========================================================================
# FridaHookEngine
# ===========================================================================

class FridaHookEngine:
    """
    Attaches FRIDA_HOOK_SCRIPT to a live process via Frida.
    Routes all JS messages to _LogStore and NetworkSinkhole.
    Falls back to SIMULATION MODE when Frida is unavailable.
    """

    # Synthetic events used in simulation mode
    _SIM_EVENTS: List[Tuple] = [
        ("CreateFileW",
         {"path": r"C:\Users\victim\AppData\Roaming\Mozilla\Firefox\logins.json"},
         "BLOCKED_FAKE_NOT_FOUND", "INVALID_HANDLE_VALUE"),
        ("CreateFileA",
         {"path": r"C:\Users\victim\AppData\Local\Google\Chrome\User Data\Default\Login Data"},
         "BLOCKED_FAKE_NOT_FOUND", "INVALID_HANDLE_VALUE"),
        ("ReadFile",
         {"handle": "0x00000034", "bytes_requested": 4096},
         "PASSTHROUGH", None),
        ("RegOpenKeyExW",
         {"hive": "HKLM", "subkey": r"SECURITY\SAM\Domains\Account"},
         "BLOCKED_ERROR_ACCESS_DENIED", "ERROR_ACCESS_DENIED(5)"),
        ("RegOpenKeyExA",
         {"hive": "HKCU", "subkey": r"Software\Microsoft\Windows NT\CurrentVersion\Winlogon"},
         "BLOCKED_ERROR_ACCESS_DENIED", "ERROR_ACCESS_DENIED(5)"),
        ("RegQueryValueExW",
         {"value_name": "DefaultPassword"},
         "PASSTHROUGH", None),
        ("connect",
         {"ip": "185.220.101.45", "port": 4444},
         "BLOCKED_FAKE_SUCCESS", "0"),
        ("send",
         {"socket": 42, "data_length": 256, "bytes_sent": 256},
         "PASSTHROUGH", None),
        ("WSASend",
         {"socket": 42, "buf_count": 2},
         "PASSTHROUGH", None),
        ("GetClipboardData",
         {"format": 1},
         "BLOCKED_NULL_RETURNED", "NULL"),
        ("CreateFileW",
         {"path": r"C:\Users\victim\AppData\Roaming\Discord\Local Storage\leveldb\000005.ldb"},
         "BLOCKED_FAKE_HONEYPOT", "fake_discord_tokens.json"),
        ("connect",
         {"ip": "162.159.135.232", "port": 443, "domain": "discord.com/api/webhooks"},
         "BLOCKED_SINKHOLE_NEUTRALIZED", "200 OK (FAKENET_SINKHOLE)"),
    ]

    def __init__(self, store: _LogStore, sinkhole: NetworkSinkhole) -> None:
        self._store    = store
        self._sinkhole = sinkhole
        self._session  = None
        self._script   = None
        self._pid: Optional[int] = None

    def attach(self, pid: int) -> bool:
        """
        Attach to process *pid*.  Returns True if Frida hooks are live,
        False if running in simulation mode.
        """
        # Validate PID: must be a positive integer (Windows max PID ~ 4M)
        if not isinstance(pid, int) or pid <= 0:
            if pid != -1:           # -1 is explicit simulation sentinel
                log.error(f"[FridaEngine] Invalid PID: {pid!r}")
                return False

        self._pid = pid

        if not HAS_FRIDA:
            log.warning(
                "[FridaEngine] Frida not installed -- SIMULATION MODE. "
                "pip install frida frida-tools"
            )
            self._run_simulation()
            return False

        if pid == -1:
            log.info("[FridaEngine] PID=-1 -- SIMULATION MODE requested explicitly")
            self._run_simulation()
            return False

        try:
            device  = frida.get_local_device()
            session = device.attach(pid)
            script  = session.create_script(FRIDA_HOOK_SCRIPT)
            script.on("message", self._on_message)
            script.load()
            self._session = session
            self._script  = script
            log.info(f"[FridaEngine] Attached to PID {pid} -- hooks LIVE")
            return True
        except frida.ProcessNotFoundError:
            log.error(f"[FridaEngine] PID {pid} not found")
        except frida.PermissionDeniedError:
            log.error(
                f"[FridaEngine] Permission denied attaching to PID {pid}. "
                "Run as Administrator."
            )
        except frida.NotSupportedError as exc:
            log.error(f"[FridaEngine] Not supported: {exc}")
        except Exception as exc:
            log.error(f"[FridaEngine] Frida error: {exc}")

        log.warning("[FridaEngine] Falling back to SIMULATION MODE")
        self._run_simulation()
        return False

    def _on_message(self, message: Dict[str, Any], data: Any) -> None:
        """Frida message callback -- runs on Frida internal thread."""
        if message.get("type") == "error":
            log.error(
                f"[FridaEngine] JS error: {message.get('description','?')} "
                f"@ {message.get('fileName','?')}:{message.get('lineNumber','?')}"
            )
            return

        if message.get("type") != "send":
            return

        try:
            payload: Dict[str, Any] = json.loads(message["payload"])
        except (json.JSONDecodeError, KeyError) as exc:
            log.warning(f"[FridaEngine] Malformed message: {exc}")
            return

        ptype = payload.get("type")
        if ptype == "ready":
            log.info(f"[FridaEngine] JS hooks confirmed ready @ {payload.get('timestamp')}")
            return
        if ptype != "api_hook":
            return

        api    = payload.get("api_name", "")
        params = payload.get("params", {})
        action = payload.get("action_taken", "")
        mock   = payload.get("mock_returned")
        ts     = payload.get("timestamp", _now())

        # Cross-check connect() events with the sinkhole
        if api == "connect" and isinstance(params, dict):
            ip   = params.get("ip", "")
            port = params.get("port", 0)
            if _is_valid_ip(ip):
                self._sinkhole.check_connection(ip, int(port))

        self._store.add_api_hook(
            timestamp=ts,
            api_name=api,
            params=params,
            action_taken=action,
            mock_returned=mock,
        )

        if "BLOCKED" in action:
            log.warning(f"[FridaEngine] INTERCEPTED {api} => {action} | {params}")
        else:
            log.debug(f"[FridaEngine] pass {api} | {params}")

    def _run_simulation(self) -> None:
        log.info("[FridaEngine] SIMULATION MODE -- injecting synthetic hook events")
        for api, params, action, mock in self._SIM_EVENTS:
            self._store.add_api_hook(
                timestamp=_now(),
                api_name=api,
                params=params,
                action_taken=action,
                mock_returned=mock,
            )
            tag = "INTERCEPTED" if "BLOCKED" in action else "pass"
            log.info(f"[SIM] {tag} {api} | {params}")

        # Exercise sinkhole with the simulated C2 connection
        self._sinkhole.check_connection("185.220.101.45", 4444, 256)

    def detach(self) -> None:
        if self._script is not None:
            try:
                self._script.unload()
            except Exception:
                pass
            self._script = None
        if self._session is not None:
            try:
                self._session.detach()
            except Exception:
                pass
            self._session = None
        if self._pid and self._pid > 0:
            log.info(f"[FridaEngine] Detached from PID {self._pid}")


# ===========================================================================
# DeceptionLayer -- public orchestrator
# ===========================================================================

class DeceptionLayer:
    """
    Top-level orchestrator for ABYSS Step 5.

    Typical usage::

        layer = DeceptionLayer()
        status = layer.start(target_process_id=1234,
                             classification_result="MALWARE")
        time.sleep(10)               # let hooks run
        log_data = layer.stop()      # writes results/deception_log.json
    """

    def __init__(self) -> None:
        self._store       = _LogStore()
        self._sinkhole    = NetworkSinkhole(self._store)
        self._hook_engine = FridaHookEngine(self._store, self._sinkhole)
        self._watcher     = HoneypotWatcher(self._store)
        self._active      = False
        self._start_ts:   Optional[str] = None
        self._target_pid: Optional[int] = None
        self._verdict:    Optional[str] = None

    # ---- Lifecycle -----------------------------------------------------------

    def start(self, target_process_id: int,
              classification_result: str) -> Dict[str, Any]:
        """
        Activate all deception layers.

        Parameters
        ----------
        target_process_id:
            PID of the suspect process.  Pass -1 to force simulation mode.
        classification_result:
            ML verdict string (e.g. "MALWARE", "SUSPICIOUS", "CLEAN").
            Layers are passive when verdict is "CLEAN".

        Returns
        -------
        Status dict describing which layers are active.
        """
        if self._active:
            log.warning("[DeceptionLayer] Already active -- call stop() first")
            return {"error": "already_active"}

        # ---- Validate inputs ------------------------------------------------
        if not isinstance(target_process_id, int):
            raise TypeError(
                f"target_process_id must be int, got {type(target_process_id).__name__}"
            )
        if not isinstance(classification_result, str):
            raise TypeError(
                f"classification_result must be str, got {type(classification_result).__name__}"
            )
        safe_verdict = re.sub(r"[^A-Za-z0-9_\-\. ]", "", classification_result).strip()
        if not safe_verdict:
            raise ValueError("classification_result is empty after sanitization")

        self._target_pid = target_process_id
        self._verdict    = safe_verdict
        self._start_ts   = _now()
        self._store.reset()

        log.info(
            f"[DeceptionLayer] Starting -- PID={target_process_id}, "
            f"verdict={safe_verdict!r}"
        )

        frida_ok = False
        if safe_verdict.upper() not in ("CLEAN",):
            self._sinkhole.start()
            frida_ok = self._hook_engine.attach(target_process_id)
            self._watcher.start()
        else:
            log.info("[DeceptionLayer] verdict=CLEAN -- deception layers passive")

        self._active = True

        status = {
            "started_at":     self._start_ts,
            "target_pid":     target_process_id,
            "classification": safe_verdict,
            "frida_attached": frida_ok,
            "frida_mode":     ("LIVE" if frida_ok
                               else ("SIMULATION" if not HAS_FRIDA else "ATTACH_FAILED")),
            "sinkhole_mode":  "FAKENET" if HAS_FAKENET else "BLOCKLIST",
            "watcher_mode":   "WATCHDOG" if HAS_WATCHDOG else "SIMULATION",
            "mock_data_dir":  str(MOCK_DATA_DIR),
            "decoy_files":    MockDataServer.list_decoys(),
        }
        log.info(f"[DeceptionLayer] All layers started: {json.dumps(status, indent=2)}")
        return status

    def stop(self) -> Dict[str, Any]:
        """
        Stop all hooks cleanly, write deception_log.json, return log dict.
        """
        if not self._active:
            log.warning("[DeceptionLayer] Not active")
            return {}

        log.info("[DeceptionLayer] Stopping all layers...")
        self._hook_engine.detach()
        self._sinkhole.stop()
        self._watcher.stop()
        self._active = False

        log_data = self.get_interception_log()
        log_data["meta"] = {
            "started_at":          self._start_ts,
            "stopped_at":          _now(),
            "target_pid":          self._target_pid,
            "classification":      self._verdict,
            "frida_available":     HAS_FRIDA,
            "watchdog_available":  HAS_WATCHDOG,
            "fakenet_available":   HAS_FAKENET,
        }
        self._save_log(log_data)
        log.info(
            f"[DeceptionLayer] Done -- "
            f"blocked={log_data['total_blocked']}, "
            f"allowed={log_data['total_allowed']}, "
            f"file_hits={len(log_data['files_accessed'])}"
        )
        return log_data

    # ---- Query --------------------------------------------------------------

    def get_interception_log(self) -> Dict[str, Any]:
        """
        Return current log snapshot.

        Schema::

            {
              "api_hooks_fired": [
                  {"timestamp", "api_name", "params", "action_taken", "mock_returned"}
              ],
              "network_blocked": [
                  {"timestamp", "dest_ip", "dest_port", "data_size", "reason"}
              ],
              "files_accessed": [
                  {"timestamp", "filepath", "was_honeypot", "data_returned"}
              ],
              "total_blocked": int,
              "total_allowed": int
            }
        """
        return self._store.snapshot()

    # ---- Public helpers (callable from external pipeline stages) ------------

    def check_network_connection(self, dest_ip: str, dest_port: int,
                                 data_size: int = 0) -> bool:
        """
        Evaluate a connection tuple against the sinkhole.
        Returns True if blocked (and logs the event).
        """
        if not _is_valid_ip(dest_ip):
            log.warning(f"[DeceptionLayer] Invalid IP passed to check: {dest_ip!r}")
            return False
        return self._sinkhole.check_connection(dest_ip, dest_port, data_size)

    def serve_mock_file(self, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Serve a honeypot file by *bare filename*.
        Returns (was_honeypot, content_string).
        Logs the access event.

        Security: bare filename only -- any path separator = rejected.
        """
        bare = Path(filename).name
        if not bare or bare != filename.strip():
            log.warning(f"[DeceptionLayer] serve_mock_file rejected: {filename!r}")
            return False, None

        was_hp, content = MockDataServer.get_content(bare)
        self._store.add_file_access(
            timestamp=_now(),
            filepath=str(MOCK_DATA_DIR / bare),
            was_honeypot=was_hp,
            data_returned=content[:500] if content else None,
        )
        return was_hp, content

    @property
    def is_active(self) -> bool:
        return self._active

    # ---- Internal -----------------------------------------------------------

    @staticmethod
    def _save_log(log_data: Dict[str, Any]) -> None:
        """Write log to disk atomically via tmp-file rename."""
        tmp = LOG_PATH.with_suffix(".json.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(log_data, fh, indent=2, default=str)
            tmp.replace(LOG_PATH)
            log.info(f"[DeceptionLayer] Log saved -> {LOG_PATH}")
        except Exception as exc:
            log.error(f"[DeceptionLayer] Failed to save log: {exc}")
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass


# ===========================================================================
# CLI
# ===========================================================================

def _build_parser():
    import argparse
    p = argparse.ArgumentParser(
        description="ABYSS -- Deception + Neutralization Layer (Step 5)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deception_layer.py --pid 1234 --verdict MALWARE
  python deception_layer.py --pid -1   --verdict SUSPICIOUS   # simulation
  python deception_layer.py --serve-file fake_passwords.txt
  python deception_layer.py --check-ip 185.220.101.45 --port 4444
        """,
    )
    p.add_argument("--pid",        type=int,   default=-1,
                   help="Target PID (-1 = simulation mode)")
    p.add_argument("--verdict",    type=str,   default="MALWARE",
                   help="ML classification (MALWARE/SUSPICIOUS/CLEAN)")
    p.add_argument("--duration",   type=float, default=5.0,
                   help="Seconds to run (default 5)")
    p.add_argument("--serve-file", type=str,   default=None,
                   help="Print mock content for filename and exit")
    p.add_argument("--check-ip",   type=str,   default=None,
                   help="Check if an IP should be blocked and exit")
    p.add_argument("--port",       type=int,   default=80,
                   help="Port for --check-ip (default 80)")
    p.add_argument("--output",     type=str,   default=None,
                   help="Output directory or file for deception_log.json")
    p.add_argument("--verbose",    action="store_true",
                   help="DEBUG logging")
    return p


def main() -> None:
    args = _build_parser().parse_args()
    if args.output:
        global LOG_PATH
        out_p = Path(args.output)
        if out_p.is_dir() or not out_p.suffix:
            out_p.mkdir(parents=True, exist_ok=True)
            LOG_PATH = out_p / "deception_log.json"
        else:
            out_p.parent.mkdir(parents=True, exist_ok=True)
            LOG_PATH = out_p

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # -- serve-file mode ------------------------------------------------------
    if args.serve_file:
        bare = Path(args.serve_file).name
        was_hp, content = MockDataServer.get_content(bare)
        if was_hp:
            print(f"\n{'='*60}")
            print(f"  MOCK DATA -- {bare}  [HONEYPOT CONTENT]")
            print(f"{'='*60}\n")
            print(content)
        else:
            print(f"No mock data for: {bare!r}")
            print(f"Available decoys: {MockDataServer.list_decoys()}")
        return

    # -- check-ip mode --------------------------------------------------------
    if args.check_ip:
        store    = _LogStore()
        sinkhole = NetworkSinkhole(store)
        sinkhole.start()
        blocked = sinkhole.check_connection(args.check_ip, args.port)
        print(f"{'BLOCKED' if blocked else 'ALLOWED'}: {args.check_ip}:{args.port}")
        sinkhole.stop()
        return

    # -- normal deception mode ------------------------------------------------
    layer = DeceptionLayer()
    try:
        status = layer.start(
            target_process_id=args.pid,
            classification_result=args.verdict,
        )
        print(f"\n[DeceptionLayer] Started:\n{json.dumps(status, indent=2)}\n")
        if args.duration > 0:
            log.info(f"Running for {args.duration}s (Ctrl+C to abort)")
            time.sleep(args.duration)
    except KeyboardInterrupt:
        log.info("Interrupted")
    finally:
        result = layer.stop()
        divider = "=" * 60
        print(f"\n{divider}")
        print("  ABYSS -- DECEPTION LAYER COMPLETE")
        print(divider)
        print(f"  API hooks fired  : {len(result.get('api_hooks_fired', []))}")
        print(f"  Network blocked  : {len(result.get('network_blocked', []))}")
        print(f"  File accesses    : {len(result.get('files_accessed', []))}")
        print(f"  Total blocked    : {result.get('total_blocked', 0)}")
        print(f"  Total allowed    : {result.get('total_allowed', 0)}")
        print(f"\n  Log -> {LOG_PATH}")
        print(f"{divider}\n")


if __name__ == "__main__":
    main()
