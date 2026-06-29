import subprocess
import time
from pathlib import Path

VBOX_MANAGE = r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"

def run_vboxmanage(args):
    cmd = [VBOX_MANAGE] + args
    print(f"Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"Error ({res.returncode}): {res.stderr.strip()}")
    return res

def main():
    # 1. Restore to clean-baseline snapshot
    print("Reverting VM to clean-baseline...")
    res = run_vboxmanage(["snapshot", "StealthOS-Sandbox", "restore", "clean-baseline"])
    if res.returncode != 0:
        return
        
    # 2. Start VM headless
    print("Starting VM headless...")
    res = run_vboxmanage(["startvm", "StealthOS-Sandbox", "--type", "headless"])
    if res.returncode != 0:
        return

    # 3. Poll showvminfo for running state
    print("Polling VM status...")
    timeout = 60
    start_time = time.time()
    while time.time() - start_time < timeout:
        res = run_vboxmanage(["showvminfo", "StealthOS-Sandbox", "--machinereadable"])
        if res.returncode == 0:
            # Parse state
            state_line = [line for line in res.stdout.splitlines() if line.startswith("VMState=")]
            if state_line:
                state = state_line[0].split("=")[1].strip('"')
                print(f"Current VM State: {state}")
                if state == "running":
                    print("VM is running successfully!")
                    break
        time.sleep(3)
    else:
        print("Timeout waiting for VM to start.")

if __name__ == "__main__":
    main()
