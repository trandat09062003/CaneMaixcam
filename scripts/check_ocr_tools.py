import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=5)

cmd = """
which tesseract
pip list | grep -i ocr
python3 -c "import cv2; print('cv2 version:', cv2.__version__)"
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print("OUT:\n", stdout.read().decode())
ssh.close()
