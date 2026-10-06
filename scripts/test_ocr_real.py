import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=5)

test_script = """import requests, json, cv2, numpy as np

OCR_API_URL = 'https://api.ocr.space/parse/image'
OCR_API_KEY = 'K82394297788957'

# Tao 1 anh test chua chu so ve so
img = np.ones((160, 640, 3), dtype=np.uint8) * 255
cv2.putText(img, 'XSKT BAC LIEU: 294185', (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 3)
_, enc = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

files = {'file': ('ticket.jpg', enc.tobytes(), 'image/jpeg')}
payload = {
    'apikey': OCR_API_KEY,
    'language': 'vnm',
    'filetype': 'JPG',
    'isOverlayRequired': False,
    'detectOrientation': False,
    'scale': True
}
print('Gui anh len OCR Space voi timeout=(10.0, 25.0)...')
r = requests.post(OCR_API_URL, files=files, data=payload, timeout=(10.0, 25.0))
print('HTTP status:', r.status_code)
res = r.json()
print('ExitCode:', res.get('OCRExitCode'))
parsed_list = res.get('ParsedResults', [])
if parsed_list:
    text = parsed_list[0].get('ParsedText', '')
    print("Ket qua nhan dien text: " + repr(text))
"""

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_ocr_real.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_ocr_real.py')
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
