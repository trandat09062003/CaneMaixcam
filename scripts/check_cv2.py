import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('10.225.139.1', username='root', password='root', timeout=4)
    stdin, stdout, stderr = ssh.exec_command('python3 -c "import cv2; print(\'cv2:\', cv2.__version__)" 2>&1')
    print(stdout.read().decode())
    stdin, stdout, stderr = ssh.exec_command('python3 -c "import maix.image; print(\'maix.image:\', dir(maix.image))" 2>&1')
    print(stdout.read().decode())
    ssh.close()
except Exception as e:
    print("ERR:", e)
