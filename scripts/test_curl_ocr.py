import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=5)

test_script = """import os, subprocess, json, time, cv2, numpy as np

# Tao anh ve so
img = np.ones((160, 600, 3), dtype=np.uint8) * 255
cv2.putText(img, 'XSKT BAC LIEU 294185', (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
cv2.imwrite('/tmp/lottery_test.jpg', img)

cmd = [
    'curl', '-k', '-s', '--connect-timeout', '8', '-m', '18',
    '-F', 'apikey=K82394297788957',
    '-F', 'language=vnm',
    '-F', 'filetype=JPG',
    '-F', 'isOverlayRequired=false',
    '-F', 'file=@/tmp/lottery_test.jpg',
    'https://api.ocr.space/parse/image'
]
t0 = time.time()
print('Running curl OCR...')
res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
elapsed = time.time() - t0
print(f'Done in {elapsed:.2f}s, returncode={res.returncode}')
print('STDOUT:', res.stdout[:500])
try:
    data = json.loads(res.stdout)
    parsed = data.get('ParsedResults', [{}])[0].get('ParsedText', '')
    print('PARSED TEXT:', repr(parsed))
except Exception as e:
    print('JSON error:', e)
"""

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_curl_ocr.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_curl_ocr.py')
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
