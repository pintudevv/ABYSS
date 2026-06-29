"""
StealthOS — Custom Suspicious PE Builder
========================================
Compiles a simple C program containing suspicious Windows API references
and appends a high-entropy payload overlay to simulate packed malware.
"""

import os
import random
import subprocess
from pathlib import Path

def main():
    base_dir = Path(__file__).parent
    c_source = base_dir / "test_suspicious.c"
    exe_out = base_dir / "test_suspicious.exe"

    # 1. Write the C source code
    c_code = """#include <windows.h>
#include <stdio.h>

int main() {
    printf("StealthOS Suspicious Test Binary\\n");
    
    // Dynamically load suspicious Win32 APIs commonly used by Trojans / Injection
    HMODULE hKernel = GetModuleHandleA("kernel32.dll");
    FARPROC pAlloc = GetProcAddress(hKernel, "VirtualAllocEx");
    FARPROC pWrite = GetProcAddress(hKernel, "WriteProcessMemory");
    FARPROC pThread = GetProcAddress(hKernel, "CreateRemoteThread");
    
    // Dynamically load suspicious Crypt APIs used by Ransomware
    HMODULE hAdvapi = LoadLibraryA("advapi32.dll");
    FARPROC pEncrypt = GetProcAddress(hAdvapi, "CryptEncrypt");
    
    printf("Resolved pointers: %p, %p, %p, %p\\n", pAlloc, pWrite, pThread, pEncrypt);
    return 0;
}
"""
    c_source.write_text(c_code, encoding="utf-8")
    print(f"C source code written to {c_source.name}")

    # 2. Compile using MinGW GCC
    print("Compiling test_suspicious.c...")
    try:
        subprocess.run([
            "gcc", str(c_source),
            "-o", str(exe_out)
        ], check=True)
        print(f"Compilation successful: {exe_out.name}")
    except Exception as e:
        print(f"Compilation failed: {e}")
        return

    # 3. Append high-entropy random bytes (to simulate encrypted overlay/ransomware payload)
    print("Appending high-entropy overlay to simulated binary...")
    try:
        random_bytes = bytearray(random.getrandbits(8) for _ in range(120000))
        with open(exe_out, "ab") as f:
            f.write(random_bytes)
        print("High-entropy overlay appended successfully.")
    except Exception as e:
        print(f"Failed to append overlay: {e}")
        return

if __name__ == "__main__":
    main()
