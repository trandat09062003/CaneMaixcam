import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("10.225.139.1", username="root", password="root", timeout=5)

test_cam = """from maix import camera, image
import cv2, numpy as np

cam = camera.Camera(320, 240)
for i in range(5):
    img = cam.read()
    if img:
        print(f"Img format={img.format()}, width={img.width()}, height={img.height()}")
        cv_img1 = image.image2cv(img)
        cv_img2 = img.to_cv() if hasattr(img, 'to_cv') else None
        print("cv_img1 shape:", cv_img1.shape, "mean BGR:", cv_img1.mean(axis=(0,1)))
        if cv_img2 is not None:
            print("cv_img2 shape:", cv_img2.shape, "mean BGR:", cv_img2.mean(axis=(0,1)))
        cv2.imwrite('/tmp/test_cam_real.jpg', cv_img1)
        break
cam.close()
"""

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_cam_fmt.py', 'w') as f:
    f.write(test_cam)
sftp.close()

stdin, stdout, stderr = ssh.exec_command("python3 /tmp/test_cam_fmt.py")
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
