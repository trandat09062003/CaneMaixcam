import socket
import paramiko

candidates = ['10.225.139.1', '10.225.138.1', '143.0.4.1', '192.168.1.3']
found_ip = None
for ip in candidates:
    s = socket.socket()
    s.settimeout(0.5)
    if s.connect_ex((ip, 22)) == 0:
        found_ip = ip
        s.close()
        break
    s.close()

print('SSH IP found:', found_ip)
if found_ip:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(found_ip, username='root', password='root', timeout=3)
    def run_ssh(cmd):
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print('CMD:', cmd)
        print('OUT:', stdout.read().decode('utf-8', errors='ignore').strip())
        print('ERR:', stderr.read().decode('utf-8', errors='ignore').strip())
    run_ssh('cat /root/kata/model_9383.mud')
    run_ssh('python3 -c "import maix; print(maix.__version__)"')
    ssh.close()
