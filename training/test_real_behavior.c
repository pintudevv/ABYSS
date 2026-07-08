#include <windows.h>
#include <stdio.h>

int main() {
    printf("StealthOS REAL Behavior Test Binary\n");

    // 1. Actually call VirtualAllocEx on self
    HANDLE hProc = GetCurrentProcess();
    LPVOID mem = VirtualAllocEx(hProc, NULL, 4096, MEM_COMMIT, PAGE_READWRITE);
    printf("Allocated memory: %p\n", mem);

    // 2. Actually call WriteProcessMemory on self
    char data[] = "test_payload";
    SIZE_T written;
    WriteProcessMemory(hProc, mem, data, sizeof(data), &written);
    printf("Wrote %zu bytes\n", written);

    // 3. Actually open a file
    HANDLE hFile = CreateFileA("C:\\Users\\Public\\test_artifact.txt",
        GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hFile != INVALID_HANDLE_VALUE) {
        const char* msg = "stealthos test artifact\n";
        DWORD bytesWritten;
        WriteFile(hFile, msg, (DWORD)strlen(msg), &bytesWritten, NULL);
        CloseHandle(hFile);
        printf("Wrote test file\n");
    }

    // 4. Actually open a registry key
    HKEY hKey;
    RegOpenKeyExA(HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Run",
        0, KEY_READ, &hKey);
    if (hKey) RegCloseKey(hKey);
    printf("Touched registry key\n");

    // 5. Sleep so Frida's 30s window actually has something to monitor
    Sleep(3000);

    printf("Done.\n");
    return 0;
}
