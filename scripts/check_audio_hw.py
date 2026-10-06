import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    c.connect('10.225.139.1', username='root', password='root', timeout=4)
except Exception:
    c.connect('192.168.110.71', username='root', password='root', timeout=4)

cmds = [
    'cat /proc/asound/cards',
    'cat /proc/asound/pcm',
    'aplay -l',
    'amixer'
]
for cmd in cmds:
    print('=== CMD:', cmd, '===', flush=True)
    stdin, stdout, stderr = c.exec_command(cmd, timeout=5)
    out = stdout.read().decode('utf-8', errors='ignore')
    print(out, flush=True)

c.close()
