import urllib.request, json, time

filepath = 'training/test_suspicious.exe'
filename = 'test_suspicious.exe'


boundary = '----TestBoundary12345'

with open(filepath, 'rb') as f:
    file_data = f.read()

body = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
    f'Content-Type: application/octet-stream\r\n\r\n'
).encode() + file_data + f'\r\n--{boundary}--\r\n'.encode()

req = urllib.request.Request(
    'http://127.0.0.1:8000/analyze',
    data=body,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
    method='POST'
)

resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
task_id = result['task_id']
print(f'Task ID: {task_id}')
print(f'Cached: {result.get("cached", False)}')

for i in range(20):
    time.sleep(3)
    try:
        status_resp = urllib.request.urlopen(f'http://127.0.0.1:8000/status/{task_id}')
        status = json.loads(status_resp.read())
        print(f'{status["progress"]:3d}% | {status["stage"]:20s} | {status["message"][:60]}')
        if status['status'] in ('done', 'error'):
            print('DONE:', status['status'])
            break
    except Exception as e:
        print(f'Poll error: {e}')
