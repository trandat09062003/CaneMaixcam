import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=5)

test_script = """import requests, json, cv2, numpy as np

OCR_API_URL = 'https://api.ocr.space/parse/image'
OCR_API_KEY = 'K82394297788957'

img = np.ones((200, 700, 3), dtype=np.uint8) * 255
cv2.putText(img, 'XSKT BAC LIEU: 294185', (30, 110), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
_, enc = cv2.imencode('.jpg', img)

files = {'file': ('test.jpg', enc.tobytes(), 'image/jpeg')}
payload = {
    'apikey': OCR_API_KEY,
    'language': 'vnm',
    'isOverlayRequired': False,
    'detectOrientation': True,
    'scale': True
}
print('Gui anh test len OCR Space...')
r = requests.post(OCR_API_URL, files=files, data=payload, timeout=15.0)
print('HTTP status:', r.status_code)
res = r.json()
print('ParsedText:', res.get('ParsedResults', [{}])[0].get('ParsedText', ''))
"""

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_ocr.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_ocr.py')
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
