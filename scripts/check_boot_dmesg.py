import paramiko
import time

time.sleep(2)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=5)

stdin, stdout, stderr = ssh.exec_command("dmesg | grep -i 'cvi' | head -n 30")
print(stdout.read().decode('utf-8', errors='ignore'))

stdin, stdout, stderr = ssh.exec_command("dmesg | grep -i 'ion' | head -n 30")
print(stdout.read().decode('utf-8', errors='ignore'))

stdin, stdout, stderr = ssh.exec_command("dmesg | grep -i 'tpu' | head -n 30")
print(stdout.read().decode('utf-8', errors='ignore'))

ssh.close()
