import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=4)

modules = ['pinmap', 'gpio', 'time', 'app', 'audio', 'camera', 'display', 'image', 'nn']
for m in modules:
    cmd = f'python3 -c "import time; print(\'testing {m}\'); from maix import {m}; print(\'ok {m}\')"'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    print(f"[{m}]: out={repr(out)} err={repr(err)}")

ssh.close()
