import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=5)

remote_test = '''
from maix import camera, display, image
import cv2
import numpy as np

cam = camera.Camera(320, 240)
img = cam.read()
print("Camera read ok:", type(img))

cv_img = image.image2cv(img)
print("image2cv ok:", type(cv_img), cv_img.shape)

hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
print("cvtColor ok:", hsv.shape)
cam.close()
print("All Vision tests passed!")
'''

sftp = ssh.open_sftp()
with sftp.open("/tmp/test_v.py", "w") as f:
    f.write(remote_test)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /tmp/test_v.py')
print("STDOUT:\n", stdout.read().decode('utf-8', errors='ignore'))
print("STDERR:\n", stderr.read().decode('utf-8', errors='ignore'))
ssh.close()
