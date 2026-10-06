import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=5)

remote_test = '''
from maix import camera, image
import cv2
import numpy as np

cam = camera.Camera(320, 240)
img = cam.read()
cv_img = image.image2cv(img)

hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
# Tinh toan thong so mau toan anh va vung trung tam
h, w = cv_img.shape[:2]
crop = hsv[h//4:3*h//4, w//4:3*w//4]

mean_h = np.mean(crop[:, :, 0])
mean_s = np.mean(crop[:, :, 1])
mean_v = np.mean(crop[:, :, 2])

print(f"Crop HSV: H={mean_h:.1f}, S={mean_s:.1f}, V={mean_v:.1f}")

# Kiem tra cac khoang mau polymer VND:
color_ranges = {
    "20000":  [(90, 45, 50), (125, 255, 255)],   # Xanh lam sang
    "500000": [(78, 40, 30), (105, 255, 180)],   # Xanh ngoc dam
    "100000": [(35, 45, 40), (85, 255, 255)],    # Xanh la cay
    "200000": [(0, 50, 50), (18, 255, 255)],     # Do cam
    "50000":  [(135, 40, 50), (165, 255, 255)],  # Hong tim
    "10000":  [(15, 50, 40), (32, 255, 255)]     # Vang nau
}

detected = []
for label, (lower, upper) in color_ranges.items():
    mask = cv2.inRange(crop, np.array(lower), np.array(upper))
    px = cv2.countNonZero(mask)
    detected.append((px, label))

detected.sort(reverse=True)
print("Top color matches:", detected[:3])
cam.close()
'''

sftp = ssh.open_sftp()
with sftp.open("/tmp/test_crop.py", "w") as f:
    f.write(remote_test)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_crop.py')
print("STDOUT:\n", stdout.read().decode('utf-8', errors='ignore'))
print("STDERR:\n", stderr.read().decode('utf-8', errors='ignore'))
ssh.close()
