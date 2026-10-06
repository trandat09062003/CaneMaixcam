import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("10.225.139.1", username="root", password="root", timeout=5)

# Dừng main.py tạm thời để mở camera test
ssh.exec_command("/etc/init.d/S99smartcane stop; killall -9 python3 2>/dev/null; sleep 1")

test_script = """import time, cv2, numpy as np
from maix import camera

cam = camera.Camera(320, 240)
print('Camera opened. Reading 15 frames...')
time.sleep(1)

for i in range(15):
    img = cam.read()
    if img is None:
        continue
    cv_img = img.to_cv()
    h_img, w_img = cv_img.shape[:2]
    margin_x = int(w_img * 0.15)
    margin_y = int(h_img * 0.15)
    roi_bgr = cv_img[margin_y:h_img - margin_y, margin_x:w_img - margin_x]
    roi_hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    roi_gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)

    roi_ycrcb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2YCrCb)
    skin_mask = cv2.inRange(roi_ycrcb, np.array([0, 133, 77]), np.array([255, 173, 127]))
    skin_mask = cv2.dilate(skin_mask, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)), iterations=1)
    non_skin = (skin_mask == 0)

    B = roi_bgr[:, :, 0].astype(np.int16)
    G = roi_bgr[:, :, 1].astype(np.int16)
    R = roi_bgr[:, :, 2].astype(np.int16)
    H = roi_hsv[:, :, 0]
    S = roi_hsv[:, :, 1]
    V = roi_hsv[:, :, 2]
    base_valid = non_skin & (V > 35) & (V < 250)

    m_500k = base_valid & (H >= 80) & (H <= 104) & (S >= 38) & (B >= 1.05 * R) & (G >= 1.02 * R)
    m_200k = base_valid & ((H <= 14) | (H >= 168)) & (S >= 65) & (R >= 1.25 * G) & (R >= 1.30 * B)
    m_100k = base_valid & (H >= 42) & (H <= 80) & (S >= 38) & (G >= 1.10 * R) & (G >= 1.10 * B)
    m_50k  = base_valid & (H >= 135) & (H <= 167) & (S >= 38) & (R >= 1.08 * G) & (B >= 0.92 * G)
    m_20k  = base_valid & (H >= 105) & (H <= 132) & (S >= 52) & (B >= 1.22 * R) & (B >= 1.12 * G)
    m_10k  = base_valid & (H >= 18) & (H <= 38) & (S >= 38) & (R >= 1.12 * B) & (G >= 1.02 * B) & (R <= 1.22 * G)

    counts = {
        '500000': int(np.count_nonzero(m_500k)),
        '200000': int(np.count_nonzero(m_200k)),
        '100000': int(np.count_nonzero(m_100k)),
        '50000':  int(np.count_nonzero(m_50k)),
        '20000':  int(np.count_nonzero(m_20k)),
        '10000':  int(np.count_nonzero(m_10k)),
    }
    sorted_counts = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    top_lbl, top_px = sorted_counts[0]
    second_lbl, second_px = sorted_counts[1]
    margin = float(top_px) / float(max(1, second_px))

    lap_var = cv2.Laplacian(roi_gray, cv2.CV_64F).var()
    print(f'Frame {i+1}: top={top_lbl} ({top_px}px), 2nd={second_lbl} ({second_px}px), margin={margin:.2f}, lap={lap_var:.1f}')
    time.sleep(0.15)

cam.close()
"""

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_cam_banknote.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_cam_banknote.py')
print(stdout.read().decode())
print(stderr.read().decode())

# Khởi động lại main.py
ssh.exec_command('/etc/init.d/S99smartcane restart')
ssh.close()
