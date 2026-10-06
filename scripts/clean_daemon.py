import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.138.1', username='root', password='root', timeout=5)

cmd = "systemctl stop smartcane; systemctl disable smartcane; killall -9 python3 2>/dev/null; rm -f /etc/systemd/system/smartcane.service; systemctl daemon-reload; echo 'CLEANUP_DONE'"
stdin, stdout, stderr = ssh.exec_command(cmd)
out = stdout.read().decode('utf-8', errors='ignore')
print("OUTPUT:\n", out)
ssh.close()
