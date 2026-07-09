"""
StealthOS — Sandbox Runner (Step 3)
====================================
Skills applied:
  - weaponized-autism : handle ALL edge cases — Cuckoo offline, timeout, malformed JSON
  - meth-lab          : no redundant abstractions, fast polling, clean fallback path
  - malware-analyst   : correct IOC extraction, realistic API call taxonomy
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("sandbox_runner")

RESULTS_DIR = Path(__file__).parent / "results"
CUCKOO_URL = "http://localhost:8090"
POLL_INTERVAL = 10   # seconds
TIMEOUT = 120        # seconds


# ---------------------------------------------------------------------------
# Cuckoo REST client
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# VirtualBox sandbox orchestration
# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

VBOX_MANAGE = r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
VM_NAME = "StealthOS-Sandbox"
SNAPSHOT_NAME = "clean-baseline"
GUEST_USER = os.getenv("STEALTHOS_VM_USER", "piyuzz")
GUEST_PASS = os.getenv("STEALTHOS_VM_PASS", "")
GUEST_PYTHON = r"C:\Users\piyuzz\AppData\Local\Programs\Python\Python313\python.exe"

import subprocess

def _run_vboxmanage(args: list[str]) -> subprocess.CompletedProcess:
    cmd = [VBOX_MANAGE] + args
    log.info(f"VBoxManage executing: {' '.join(cmd)}")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        log.warning(f"VBoxManage command returned non-zero ({res.returncode}): {res.stderr.strip()}")
    return res

def _vbox_restore() -> bool:
    """Restores the VM to the baseline snapshot."""
    log.info("Reverting VM to clean-baseline snapshot...")
    res = _run_vboxmanage(["snapshot", VM_NAME, "restore", SNAPSHOT_NAME])
    return res.returncode == 0

def _wait_for_guest_additions(timeout: int = 180) -> bool:
    """Polls a simple command in the guest to verify Guest Additions are ready.
    Allows up to 180s for full headless Windows boot with AutoLogon (~60-70s typically).
    """
    log.info("Waiting for Guest Additions to become active...")
    # Give Windows time to complete boot before first poll
    log.info("Initial 35s grace period for Windows boot + AutoLogon...")
    time.sleep(35)
    start_time = time.time()
    while time.time() - start_time < timeout:
        res = _run_vboxmanage([
            "guestcontrol", VM_NAME, "run",
            "--exe", "C:\\Windows\\System32\\cmd.exe",
            "--username", GUEST_USER,
            "--password", GUEST_PASS,
            "--", "/c", "echo ready"
        ])
        if res.returncode == 0:
            log.info("Guest Additions are active and responsive!")
            return True
        time.sleep(5)
    return False

def _vbox_start() -> bool:
    """Starts the VM headless (live snapshot with defaultfrontend=headless) and polls until 'running'."""
    log.info("Starting VM headless...")
    res = _run_vboxmanage(["startvm", VM_NAME, "--type", "headless"])
    if res.returncode != 0:
        return False

    # Poll VM state
    timeout = 60
    start_time = time.time()
    while time.time() - start_time < timeout:
        res = _run_vboxmanage(["showvminfo", VM_NAME, "--machinereadable"])
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if line.startswith("VMState="):
                    state = line.split("=")[1].strip('"')
                    log.info(f"Current VM State: {state}")
                    if state == "running":
                        # Wait dynamically for Guest Additions to start
                        return _wait_for_guest_additions()
        time.sleep(3)
    return False

def _vbox_copyto(host_path: Path, guest_dir: str) -> bool:
    if not guest_dir.endswith("\\"):
        guest_dir = guest_dir + "\\"
    """Copies a file from the host into the guest."""
    log.info(f"Copying {host_path.name} to guest directory {guest_dir}...")
    res = _run_vboxmanage([
        "guestcontrol", VM_NAME, "copyto",
        f"--target-directory={guest_dir}",
        "--username", GUEST_USER,
        "--password", GUEST_PASS,
        str(host_path)
    ])
    return res.returncode == 0

def _vbox_run(exe_path: str, args: list[str]) -> bool:
    """Runs an executable inside the guest."""
    log.info(f"Running command inside guest: {exe_path} {' '.join(args)}...")
    res = _run_vboxmanage([
        "guestcontrol", VM_NAME, "run",
        "--exe", exe_path,
        "--username", GUEST_USER,
        "--password", GUEST_PASS,
        "--timeout", "150000",
        "--"
    ] + args)
    log.info(f"GUEST STDOUT:\n{res.stdout}")
    log.info(f"GUEST STDERR:\n{res.stderr}")
    return res.returncode == 0

def _vbox_copyfrom(guest_path: str, host_path: Path) -> bool:
    target_dir_str = str(host_path.parent)
    if not target_dir_str.endswith("\\"):
        target_dir_str = target_dir_str + "\\"
    """Copies a file from the guest back to the host."""
    log.info(f"Copying {guest_path} back from guest to {host_path}...")
    res = _run_vboxmanage([
        "guestcontrol", VM_NAME, "copyfrom",
        f"--target-directory={target_dir_str}",
        "--username", GUEST_USER,
        "--password", GUEST_PASS,
        guest_path
    ])
    # VirtualBox copyfrom might save it as host_path.parent / basename_of_guest_path
    # Let's ensure it is renamed to host_path if names differ
    src_file = host_path.parent / guest_path.split("\\")[-1]
    if res.returncode == 0 and src_file.exists() and src_file != host_path:
        if host_path.exists():
            os.remove(host_path)
        os.rename(src_file, host_path)
    return res.returncode == 0

def _vbox_poweroff() -> bool:
    """Powers off the VM."""
    log.info("Powering off VM...")
    res = _run_vboxmanage(["controlvm", VM_NAME, "poweroff"])
    return res.returncode == 0


# ---------------------------------------------------------------------------
# Mock behavior generator (when Cuckoo unavailable)
# ---------------------------------------------------------------------------

_TROJAN_APIS = [
    ("VirtualAllocEx", "kernel32.dll", "memory"),
    ("WriteProcessMemory", "kernel32.dll", "memory"),
    ("CreateRemoteThread", "kernel32.dll", "process"),
    ("OpenProcess", "kernel32.dll", "process"),
    ("NtUnmapViewOfSection", "ntdll.dll", "memory"),
]
_SPYWARE_APIS = [
    ("GetClipboardData", "user32.dll", "clipboard"),
    ("SetWindowsHookEx", "user32.dll", "hooking"),
    ("GetAsyncKeyState", "user32.dll", "keyboard"),
    ("RegOpenKeyExA", "advapi32.dll", "registry"),
]
_RANSOMWARE_APIS = [
    ("CryptEncrypt", "advapi32.dll", "crypto"),
    ("CryptGenKey", "advapi32.dll", "crypto"),
    ("DeleteFileA", "kernel32.dll", "filesystem"),
    ("MoveFileExA", "kernel32.dll", "filesystem"),
    ("FindFirstFileA", "kernel32.dll", "filesystem"),
]
_NETWORK_APIS = [
    ("connect", "ws2_32.dll", "network"),
    ("send", "ws2_32.dll", "network"),
    ("WSASend", "ws2_32.dll", "network"),
    ("InternetOpenA", "wininet.dll", "network"),
    ("HttpSendRequestA", "wininet.dll", "network"),
]
_COMMON_APIS = [
    ("CreateFileA", "kernel32.dll", "filesystem"),
    ("ReadFile", "kernel32.dll", "filesystem"),
    ("WriteFile", "kernel32.dll", "filesystem"),
    ("LoadLibraryA", "kernel32.dll", "process"),
    ("GetProcAddress", "kernel32.dll", "process"),
    ("RegQueryValueExA", "advapi32.dll", "registry"),
    ("GetSystemInfo", "kernel32.dll", "system"),
    ("IsDebuggerPresent", "kernel32.dll", "anti_debug"),
]

_FAKE_IPS = [
    "185.220.101.45", "194.165.16.52", "45.142.212.100",
    "91.92.251.103", "178.128.83.165", "104.21.45.67",
]
_FAKE_DOMAINS = [
    "update-service.pw", "cdn-analytics.xyz", "telemetry-check.net",
    "secure-auth.top", "license-verify.info",
]
_FAKE_REGISTRY_KEYS = [
    r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run\SvcHost32",
    r"HKLM\System\CurrentControlSet\Services\FakeSvc",
    r"HKCU\Software\Microsoft\Windows NT\CurrentVersion\Winlogon",
    r"HKLM\Software\Microsoft\Windows\CurrentVersion\RunOnce\Update",
]
_FAKE_PATHS = [
    r"C:\Users\victim\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\update.exe",
    r"C:\Windows\Temp\svchost32.exe",
    r"C:\ProgramData\Microsoft\Windows\update.dll",
    r"C:\Users\victim\Documents\important_file.docx.enc",
]


def _generate_mock_behavior(file_path: Path, features: dict) -> dict:
    """
    Generate realistic mock behavior based on static features.
    Used when Cuckoo is not available.
    """
    risk = features.get("heuristic_risk", {})
    risk_score = risk.get("score", 20)
    pe = features.get("pe_analysis", {})
    strings = features.get("string_analysis", {})
    dangerous_imports = {d["function"] for d in pe.get("dangerous_imports", [])}
    suspicious_hits = {h["pattern"] for h in strings.get("suspicious_hits", [])}

    # Decide threat profile from static indicators
    is_ransomware = any(k in dangerous_imports or k in suspicious_hits
                        for k in ["CryptEncrypt", "ransom", "bitcoin", "CryptGenKey"])
    is_spyware = any(k in dangerous_imports or k in suspicious_hits
                     for k in ["GetClipboardData", "keylog", "GetAsyncKeyState"])
    is_trojan = any(k in dangerous_imports
                    for k in ["CreateRemoteThread", "WriteProcessMemory", "VirtualAllocEx"])

    # Build API call timeline
    base_time = datetime.now()
    api_calls = []
    chosen_apis = list(_COMMON_APIS)
    if risk_score > 20: chosen_apis += _NETWORK_APIS
    if is_ransomware:    chosen_apis += _RANSOMWARE_APIS
    if is_spyware:       chosen_apis += _SPYWARE_APIS
    if is_trojan:        chosen_apis += _TROJAN_APIS

    for i, (api, dll, cat) in enumerate(chosen_apis[:30]):
        ts = (base_time + timedelta(milliseconds=i * random.randint(50, 300))).isoformat()
        api_calls.append({
            "timestamp": ts,
            "process": file_path.name,
            "api": api,
            "dll": dll,
            "category": cat,
            "status": 1,
            "return_value": "0x0" if cat != "crypto" else "0x1",
            "arguments": [],
        })

    # Network connections
    net_connections = []
    if risk_score > 15:
        for ip in random.sample(_FAKE_IPS, min(3, len(_FAKE_IPS))):
            net_connections.append({
                "dst_ip": ip,
                "dst_port": random.choice([80, 443, 4444, 8080, 6667]),
                "protocol": random.choice(["TCP", "HTTPS"]),
                "domain": random.choice(_FAKE_DOMAINS),
            })

    # Registry operations
    reg_ops = []
    if risk_score > 25 or is_ransomware or is_trojan:
        for key in random.sample(_FAKE_REGISTRY_KEYS, min(2, len(_FAKE_REGISTRY_KEYS))):
            reg_ops.append({"key": key, "operation": "SetValue", "blocked": False})
        reg_ops.append({
            "key": r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
            "operation": "SetValue", "blocked": False,
        })

    # File operations
    file_ops = []
    for path in random.sample(_FAKE_PATHS, min(2, len(_FAKE_PATHS))):
        file_ops.append({
            "path": path,
            "operation": "write" if is_ransomware else "read",
            "suspicious": True,
        })

    return {
        "mock_mode": True,
        "mock_reason": "cuckoo_unavailable",
        "cuckoo_task_id": None,
        "analysis_duration_seconds": 45,
        "api_calls": api_calls,
        "registry_operations": reg_ops,
        "file_operations": file_ops,
        "processes": [
            {"name": file_path.name, "pid": random.randint(1000, 9999),
             "parent_pid": 4, "command_line": str(file_path)},
            {"name": "cmd.exe", "pid": random.randint(1000, 9999),
             "parent_pid": 4, "command_line": "cmd.exe /c ipconfig"},
        ] if risk_score > 20 else [
            {"name": file_path.name, "pid": random.randint(1000, 9999),
             "parent_pid": 4, "command_line": str(file_path)},
        ],
        "network_connections": net_connections,
        "score": min(risk_score, 10),
        "signatures": (
            (["ransomware_behavior", "file_encryption"] if is_ransomware else []) +
            (["spyware_clipboard", "keylogger"] if is_spyware else []) +
            (["process_injection", "hollowing"] if is_trojan else []) +
            (["network_activity"] if net_connections else [])
        ),
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_sandbox(file_path: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    features_path = output_dir / "features.json"
    features: dict = {}
    if features_path.exists():
        try:
            features = json.loads(features_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    behavior: dict = {}
    success = False

    try:
        log.info("Starting VirtualBox VM dynamic profiling sequence...")
        
        # 1. Revert to clean baseline
        if not _vbox_restore():
            raise RuntimeError("Failed to restore clean-baseline snapshot.")
            
        # 2. Boot VM
        if not _vbox_start():
            raise RuntimeError("Failed to boot guest VM into running state.")

        # 3. Copy guest_sandbox.py script to guest desktop
        guest_sandbox_script = Path(__file__).parent / "guest_sandbox.py"
        if not _vbox_copyto(guest_sandbox_script, "C:\\Users\\piyuzz\\Desktop"):
            raise RuntimeError("Failed to copy guest_sandbox.py helper into guest VM.")

        # 4. Copy target analysis file to guest desktop
        if not _vbox_copyto(file_path, "C:\\Users\\piyuzz\\Desktop"):
            raise RuntimeError("Failed to copy target executable into guest VM.")

        # 5. Run the guest Frida hook monitor script (takes 30 seconds to trace execution)
        guest_target_exe = f"C:\\Users\\piyuzz\\Desktop\\{file_path.name}"
        guest_behavior_json = "C:\\Users\\piyuzz\\Desktop\\behavior_result.json"
        
        run_args = [
            "C:\\Users\\piyuzz\\Desktop\\guest_sandbox.py",
            guest_target_exe,
            guest_behavior_json
        ]
        
        run_ok = _vbox_run(GUEST_PYTHON, run_args)
        # Even if VBoxManage timed out (VERR_TIMEOUT), the script may have
        # completed and written the result file — always attempt to copy it.
        if not run_ok:
            log.warning("guestcontrol run returned non-zero; attempting to copy result anyway (VERR_TIMEOUT case).")

        # 6. Copy behavior_result.json back to output_dir / behavior.json
        out_path = output_dir / "behavior.json"
        if not _vbox_copyfrom(guest_behavior_json, out_path):
            raise RuntimeError("Failed to copy behavior_result.json back from guest VM.")

        # 7. Poweroff VM
        _vbox_poweroff()
        
        # 8. Restore clean baseline again
        _vbox_restore()
        
        # Load behavior report
        if out_path.exists():
            behavior = json.loads(out_path.read_text(encoding="utf-8"))
            success = True
            log.info("VirtualBox VM dynamic profiling completed successfully.")

    except Exception as e:
        log.error(f"VirtualBox dynamic profiling failed: {e}. Falling back to emulated profiling.")
        # Ensure VM is powered off and reverted on failure to avoid leaving running VM
        try:
            _vbox_poweroff()
            _vbox_restore()
        except Exception:
            pass

    if not success:
        log.info("Generating mock dynamic profile fallback...")
        behavior = _generate_mock_behavior(file_path, features)
        behavior["is_simulated"] = True  # Flag to clearly mark simulated fallback data

    # Save final report to output directory
    out_path = output_dir / "behavior.json"
    out_path.write_text(json.dumps(behavior, indent=2, default=str), encoding="utf-8")

    api_count = len(behavior.get("api_calls", []))
    net_count = len(behavior.get("network_connections", []))
    log.info(f"Behavior saved → {api_count} API calls, {net_count} network connections")
    log.info(f"Output: {out_path}")
    return behavior


def main():
    parser = argparse.ArgumentParser(description="StealthOS Sandbox Runner — Step 3")
    parser.add_argument("file", nargs="?", help="File to analyze")
    parser.add_argument("--output", "-o", default=str(RESULTS_DIR))
    args = parser.parse_args()

    if not args.file:
        parser.print_help()
        sys.exit(1)

    file_path = Path(args.file).resolve()
    if not file_path.exists():
        log.error(f"File not found: {file_path}")
        sys.exit(1)

    behavior = run_sandbox(file_path, Path(args.output))
    print(f"\n  Sandbox complete — mock_mode={behavior.get('mock_mode')}")
    print(f"  API calls     : {len(behavior.get('api_calls', []))}")
    print(f"  Network conns : {len(behavior.get('network_connections', []))}")
    print(f"  Registry ops  : {len(behavior.get('registry_operations', []))}")


if __name__ == "__main__":
    main()
