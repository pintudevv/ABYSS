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
    
    # Frida JavaScript hooking script
    js_code = """
    'use strict';
    var _cachedModules = null;
    
    function findFunc(name) {
        // Try static API (Frida older versions)
        try {
            var p = Module.findExportByName(null, name);
            if (p) return p;
        } catch(e) {}
        // Try instance-based search via cached module list (Frida 16+/17.x)
        try {
            if (!_cachedModules) _cachedModules = Process.enumerateModules();
            for (var i = 0; i < _cachedModules.length; i++) {
                try {
                    var addr = _cachedModules[i].findExportByName(name);
                    if (addr) return addr;
                } catch(ex) {}
            }
        } catch(e2) {}
        return null;
    }
    
    function logCall(api, details) {
        send(JSON.stringify({
            api: api,
            details: details
        }));
    }
    
    // Hook CreateFile
    var pCreateFileW = findFunc("CreateFileW");
    if (pCreateFileW) {
        Interceptor.attach(pCreateFileW, {
            onEnter: function(args) {
                try {
                    var path = args[0].readUtf16String();
                    logCall("CreateFileW", path);
                } catch(e) {}
            }
        });
    }
    
    var pCreateFileA = findFunc("CreateFileA");
    if (pCreateFileA) {
        Interceptor.attach(pCreateFileA, {
            onEnter: function(args) {
                try {
                    var path = args[0].readAnsiString();
                    logCall("CreateFileA", path);
                } catch(e) {}
            }
        });
    }
    
    // Hook RegOpenKeyEx
    var pRegOpenKeyExW = findFunc("RegOpenKeyExW");
    if (pRegOpenKeyExW) {
        Interceptor.attach(pRegOpenKeyExW, {
            onEnter: function(args) {
                try {
                    var key = args[1].readUtf16String();
                    logCall("RegOpenKeyExW", key);
                } catch(e) {}
            }
        });
    }
    var pRegOpenKeyExA = findFunc("RegOpenKeyExA");
    if (pRegOpenKeyExA) {
        Interceptor.attach(pRegOpenKeyExA, {
            onEnter: function(args) {
                try {
                    var key = args[1].readAnsiString();
                    logCall("RegOpenKeyExA", key);
                } catch(e) {}
            }
        });
    }
    
    // Hook VirtualAllocEx
    var pVirtualAllocEx = findFunc("VirtualAllocEx");
    if (pVirtualAllocEx) {
        Interceptor.attach(pVirtualAllocEx, {
            onEnter: function(args) {
                logCall("VirtualAllocEx", "allocating memory");
            }
        });
    }
    
    // Hook WriteProcessMemory
    var pWriteProcessMemory = findFunc("WriteProcessMemory");
    if (pWriteProcessMemory) {
        Interceptor.attach(pWriteProcessMemory, {
            onEnter: function(args) {
                logCall("WriteProcessMemory", "writing to process memory");
            }
        });
    }
    
    // Hook CreateRemoteThread
    var pCreateRemoteThread = findFunc("CreateRemoteThread");
    if (pCreateRemoteThread) {
        Interceptor.attach(pCreateRemoteThread, {
            onEnter: function(args) {
                logCall("CreateRemoteThread", "spawning thread in remote process");
            }
        });
    }
    
    // Hook CryptEncrypt
    var pCryptEncrypt = findFunc("CryptEncrypt");
    if (pCryptEncrypt) {
        Interceptor.attach(pCryptEncrypt, {
            onEnter: function(args) {
                logCall("CryptEncrypt", "encrypting data block");
            }
        });
    }
    
    // Hook Connect
    var connectPtr = findFunc("connect");
    if (connectPtr) {
        Interceptor.attach(connectPtr, {
            onEnter: function(args) {
                try {
                    var port = (args[1].readU8(2) << 8) | args[1].readU8(3);
                    var ip = args[1].readU8(4) + "." + args[1].readU8(5) + "." + args[1].readU8(6) + "." + args[1].readU8(7);
                    logCall("connect", ip + ":" + port);
                } catch(e) {}
            }
        });
    }
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
