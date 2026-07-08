import urllib.request
import json
import time

def run_test():
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    data = []
    data.append(('--' + boundary).encode('utf-8'))
    data.append('Content-Disposition: form-data; name="file"; filename="test_suspicious.exe"'.encode('utf-8'))
    data.append('Content-Type: application/x-dosexec'.encode('utf-8'))
    data.append(''.encode('utf-8'))
    with open('training/test_suspicious.exe', 'rb') as f:
        data.append(f.read())
    data.append(('--' + boundary + '--').encode('utf-8'))
    body = b'\r\n'.join(data)

    req = urllib.request.Request('http://localhost:8000/analyze', data=body)
    req.add_header('Content-Type', 'multipart/form-data; boundary=' + boundary)
    
    print("Uploading file to http://localhost:8000/analyze...")
    try:
        res = urllib.request.urlopen(req)
        resp = json.loads(res.read().decode('utf-8'))
        task_id = resp['task_id']
        print('Task created successfully. Task ID:', task_id)
    except Exception as e:
        print("Upload failed:", e)
        return

    # Poll status
    print("Polling status...")
    while True:
        try:
            status_res = urllib.request.urlopen('http://localhost:8000/status/' + task_id)
            status_data = json.loads(status_res.read().decode('utf-8'))
            print(f'[{time.strftime("%H:%M:%S")}] Progress: {status_data["progress"]}% | Stage: {status_data["stage"]} | Message: {status_data["message"]}')
            if status_data["status"] in ('done', 'error'):
                break
        except Exception as e:
            print("Poll failed:", e)
        time.sleep(5)

    # Get final result
    print("Fetching final report...")
    try:
        report_res = urllib.request.urlopen('http://localhost:8000/results/' + task_id)
        report_data = json.loads(report_res.read().decode('utf-8'))
        print("\n" + "="*50)
        print("  REST API RESULTS:")
        print("="*50)
        print("  Filename:", report_data.get("filename"))
        print("  Threat Detected:", report_data.get("threat_detected"))
        print("  Threat Type:", report_data.get("threat_type"))
        print("  Confidence:", report_data.get("confidence"))
        print("  Risk Level:", report_data.get("risk_level"))
        print("  Classifier Used:", report_data.get("classifier_used"))
        print("="*50 + "\n")
    except Exception as e:
        print("Failed to fetch results:", e)

if __name__ == "__main__":
    run_test()
