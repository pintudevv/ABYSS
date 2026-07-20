import frida
import sys
import json
import time

def main():
    if len(sys.argv) < 3:
        print("Usage: guest_sandbox.py <target_exe> <output_json>")
        sys.exit(1)
        
    target_exe = sys.argv[1]
    output_json = sys.argv[2]
    
    print(f"Spawning target: {target_exe}")
    device = frida.get_local_device()
    pid = device.spawn([target_exe])
    session = device.attach(pid)
    
    # Frida JavaScript hooking script - compatible with Frida 16+
    js_code = r"""
    'use strict';
    
    function findFunc(name) {
        // Frida 16+: Process.enumerateModules() returns array of Module objects
        // each with findExportByName() method
        try {
            const modules = Process.enumerateModules();
            for (let i = 0; i < modules.length; i++) {
                try {
                    const addr = modules[i].findExportByName(name);
                    if (addr) return addr;
                } catch (_) {}
            }
        } catch (_) {}
        return null;
    }
    
    function logCall(api, details) {
        send(JSON.stringify({ api: api, details: details }));
    }
    
    // Hook CreateFileW
    const pCreateFileW = findFunc("CreateFileW");
    if (pCreateFileW) {
        Interceptor.attach(pCreateFileW, {
            onEnter(args) {
                try {
                    const path = args[0].readUtf16String();
                    logCall("CreateFileW", path);
                } catch (_) {}
            }
        });
    }
    
    // Hook CreateFileA
    const pCreateFileA = findFunc("CreateFileA");
    if (pCreateFileA) {
        Interceptor.attach(pCreateFileA, {
            onEnter(args) {
                try {
                    const path = args[0].readAnsiString();
                    logCall("CreateFileA", path);
                } catch (_) {}
            }
        });
    }
    
    // Hook RegOpenKeyExW
    const pRegOpenKeyExW = findFunc("RegOpenKeyExW");
    if (pRegOpenKeyExW) {
        Interceptor.attach(pRegOpenKeyExW, {
            onEnter(args) {
                try {
                    const key = args[1].readUtf16String();
                    logCall("RegOpenKeyExW", key);
                } catch (_) {}
            }
        });
    }
    
    // Hook RegOpenKeyExA
    const pRegOpenKeyExA = findFunc("RegOpenKeyExA");
    if (pRegOpenKeyExA) {
        Interceptor.attach(pRegOpenKeyExA, {
            onEnter(args) {
                try {
                    const key = args[1].readAnsiString();
                    logCall("RegOpenKeyExA", key);
                } catch (_) {}
            }
        });
    }
    
    // Hook VirtualAllocEx
    const pVirtualAllocEx = findFunc("VirtualAllocEx");
    if (pVirtualAllocEx) {
        Interceptor.attach(pVirtualAllocEx, {
            onEnter() {
                logCall("VirtualAllocEx", "allocating memory");
            }
        });
    }
    
    // Hook WriteProcessMemory
    const pWriteProcessMemory = findFunc("WriteProcessMemory");
    if (pWriteProcessMemory) {
        Interceptor.attach(pWriteProcessMemory, {
            onEnter() {
                logCall("WriteProcessMemory", "writing to process memory");
            }
        });
    }
    
    // Hook CreateRemoteThread
    const pCreateRemoteThread = findFunc("CreateRemoteThread");
    if (pCreateRemoteThread) {
        Interceptor.attach(pCreateRemoteThread, {
            onEnter() {
                logCall("CreateRemoteThread", "spawning thread in remote process");
            }
        });
    }
    
    // Hook CryptEncrypt
    const pCryptEncrypt = findFunc("CryptEncrypt");
    if (pCryptEncrypt) {
        Interceptor.attach(pCryptEncrypt, {
            onEnter() {
                logCall("CryptEncrypt", "encrypting data block");
            }
        });
    }
    
    // Hook connect
    const connectPtr = findFunc("connect");
    if (connectPtr) {
        Interceptor.attach(connectPtr, {
            onEnter(args) {
                try {
                    const port = (args[1].readU8(2) << 8) | args[1].readU8(3);
                    const ip = args[1].readU8(4) + "." + args[1].readU8(5) + "." + 
                               args[1].readU8(6) + "." + args[1].readU8(7);
                    logCall("connect", ip + ":" + port);
                } catch (_) {}
            }
        });
    }
    
    send(JSON.stringify({ api: '__frida_ready__', details: 'hooks installed' }));
    """
    
    api_calls_log = []
    def on_message(message, data):
        if message['type'] == 'send':
            payload = json.loads(message['payload'])
            if payload.get('api') == '__frida_ready__':
                print(f"FRIDA HOOKS INSTALLED: {payload.get('details', '')}")
                return
            api_calls_log.append({
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "api": payload["api"],
                "details": payload["details"]
            })
        elif message['type'] == 'error':
            print(f"FRIDA SCRIPT ERROR: {message.get('description', message)}")
            print(f"STACK: {message.get('stack', 'no stack')}")
            
    script = session.create_script(js_code)
    script.on('message', on_message)
    try:
        script.load()
    except Exception as e:
        print(f"SCRIPT LOAD FAILED: {e}")
    
    device.resume(pid)
    print("Frida script loaded. Resuming process and monitoring for 30s...")
    time.sleep(30)
    
    print("Detaching session...")
    # Kill target first so session.detach() doesn't hang
    try:
        device.kill(pid)
    except Exception:
        pass
    try:
        session.detach()
    except Exception:
        pass
        
    print(f"Captured {len(api_calls_log)} API calls.")
    
    # Format behavior report
    report = {
        "mock_mode": False,
        "cuckoo_task_id": None,
        "analysis_duration_seconds": 30,
        "api_calls": [
            {
                "timestamp": call["timestamp"],
                "process": target_exe.split("\\")[-1],
                "api": call["api"],
                "category": "monitored",
                "status": 1,
                "return_value": "0x0",
                "arguments": [call["details"]]
            }
            for call in api_calls_log
        ],
        "registry_operations": [
            {"key": call["details"], "operation": call["api"], "blocked": False}
            for call in api_calls_log if "RegOpenKey" in call["api"]
        ],
        "file_operations": [
            {"path": call["details"], "operation": call["api"], "suspicious": False}
            for call in api_calls_log if "CreateFile" in call["api"]
        ],
        "processes": [
            {"name": target_exe.split("\\")[-1], "pid": pid, "parent_pid": 0, "command_line": target_exe}
        ],
        "network_connections": [
            {
                "dst_ip": call["details"].split(":")[0],
                "dst_port": int(call["details"].split(":")[1]) if ":" in call["details"] else 0,
                "protocol": "TCP",
                "domain": ""
            }
            for call in api_calls_log if "connect" in call["api"]
        ],
        "score": len(api_calls_log) * 5,
        "signatures": []
    }
    
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Results saved to {output_json}")

if __name__ == "__main__":
    main()
