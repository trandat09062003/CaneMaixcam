import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('10.225.139.1', username='root', password='root', timeout=4)

cmds = [
    'python3 -c "from maix import pinmap; [print(p, pinmap.get_pin_functions(p)) for p in pinmap.get_pins()]"'
]
for cmd in cmds:
    print('=== CMD:', cmd, '===')
    stdin, stdout, stderr = c.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='ignore'))
    err = stderr.read().decode('utf-8', errors='ignore')
    if err:
        print('[ERR]:', err)

c.close()
