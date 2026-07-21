"""
ABYSS -- Live Frida Attachment Verification Test
=================================================
Tests Frida dynamic instrumentation attachment to an active, already-running process PID.
"""

import sys
import time
import subprocess
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

import frida
from deception_layer import DeceptionLayer

def main():
    print("=" * 65)
    print("  ABYSS -- LIVE FRIDA PROCESS ATTACHMENT TEST")
    print("=" * 65)

    print(f"\n[1] Frida Version Confirmed: {frida.__version__}")

    # Launch a standard native Win32 target process (python worker)
    print("\n[2] Launching native Win32 target process (python worker)...")
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    target_pid = proc.pid
    print(f"  -> Target Process PID: {target_pid}")
    time.sleep(1.0)  # Allow process initialization

    try:
        # Instantiate DeceptionLayer and attach hooks to live PID
        print(f"\n[3] Attaching ABYSS Deception Engine Hooks to live PID {target_pid}...")
        layer = DeceptionLayer()
        status = layer.start(target_process_id=target_pid, classification_result="MALWARE")

        print("\n  ================ ATTACHMENT RESULT ================")
        print(f"  Frida Attached : {status.get('frida_attached')}")
        print(f"  Frida Mode     : {status.get('frida_mode')}")
        print(f"  Target PID     : {status.get('target_pid')}")
        print(f"  Decoy Files    : {len(status.get('decoy_files', []))} honeypots ready")

        if status.get("frida_attached") is True:
            print("\n  [SUCCESS] Live Frida instrumentation attached to already-running PID!")
            print("  Win32 API hooks (CreateFileW, SetWindowsHookEx, BitBlt, connect) are LIVE.")
        else:
            print(f"\n  [FAILED] Frida attachment failed. Mode: {status.get('frida_mode')}")

    except Exception as exc:
        print(f"\n  [ERROR] Frida attachment exception: {exc}")

    finally:
        # Cleanup test process
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()
        print(f"\n[4] Cleaned up target test process PID {target_pid}.")
        print("=" * 65)

if __name__ == "__main__":
    main()
