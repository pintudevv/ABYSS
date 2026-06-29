#include <windows.h>
#include <stdio.h>

int main() {
    printf("StealthOS Suspicious Test Binary\n");
    
    // Dynamically load suspicious Win32 APIs commonly used by Trojans / Injection
    HMODULE hKernel = GetModuleHandleA("kernel32.dll");
    FARPROC pAlloc = GetProcAddress(hKernel, "VirtualAllocEx");
    FARPROC pWrite = GetProcAddress(hKernel, "WriteProcessMemory");
    FARPROC pThread = GetProcAddress(hKernel, "CreateRemoteThread");
    
    // Dynamically load suspicious Crypt APIs used by Ransomware
    HMODULE hAdvapi = LoadLibraryA("advapi32.dll");
    FARPROC pEncrypt = GetProcAddress(hAdvapi, "CryptEncrypt");
    
    printf("Resolved pointers: %p, %p, %p, %p\n", pAlloc, pWrite, pThread, pEncrypt);
    return 0;
}
