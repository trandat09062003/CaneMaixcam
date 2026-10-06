import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=5)

# Fix DNS and hosts
ssh.exec_command('''
echo "nameserver 1.1.1.1" > /etc/resolv.conf
echo "nameserver 192.168.110.5" >> /etc/resolv.conf
echo "nameserver 8.8.8.8" >> /etc/resolv.conf
grep -q "api.ocr.space" /etc/hosts || echo "94.130.69.140 api.ocr.space" >> /etc/hosts
''')
time.sleep(1)

test_script = """import json, subprocess, time, cv2, numpy as np

# Tao anh test nho gon (300x100) de upload cuc nhanh (< 15KB)
img = np.ones((100, 320, 3), dtype=np.uint8) * 255
cv2.putText(img, '294185', (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 0, 0), 4)
cv2.imwrite('/tmp/lottery_small.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])

cmd = [
    'curl', '-k', '-s', '--max-time', '15',
    '-F', 'apikey=K82394297788957',
    '-F', 'language=vnm',
    '-F', 'filetype=JPG',
    '-F', 'isOverlayRequired=false',
    '-F', 'file=@/tmp/lottery_small.jpg',
    'https://api.ocr.space/parse/image'
]
print('Gui anh test (10KB) len OCR Space...')
t0 = time.time()
p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
print(f'Thoi gian phan hoi: {time.time()-t0:.2f}s, code={p.returncode}')
print('KET QUA:', p.stdout)
"""

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_ocr_fast.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_ocr_fast.py')
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
