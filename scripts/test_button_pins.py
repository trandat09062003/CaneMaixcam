import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
for ip in ["10.225.139.1", "10.225.138.1", "143.0.4.1", "192.168.1.3"]:
    try:
        ssh.connect(ip, username='root', password='root', timeout=2)
        print(f"Connected to {ip}")
        break
    except:
        pass

cmd = """python3 -c "
from maix import gpio, pinmap
for p in ['A28', 'A14']:
    try:
        curr = pinmap.get_pin_function(p)
        print(f'{p} current func: {curr}')
    except Exception as e:
        print(f'{p} get_pin_function error: {e}')
    try:
        pinmap.set_pin_function(p, f'GPIO{p}')
        print(f'{p} set to GPIO{p} OK')
    except Exception as e:
        print(f'{p} set to GPIO{p} error: {e}')
    try:
        btn = gpio.GPIO(f'GPIO{p}', gpio.Mode.IN, gpio.Pull.PULL_UP)
        print(f'{p} gpio obj as GPIO{p} OK, value={btn.value()}')
    except Exception as e:
        print(f'{p} gpio obj as GPIO{p} error: {e}')
        try:
            btn = gpio.GPIO(p, gpio.Mode.IN, gpio.Pull.PULL_UP)
            print(f'{p} gpio obj as {p} OK, value={btn.value()}')
        except Exception as e2:
            print(f'{p} gpio obj as {p} error: {e2}')
"
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode('utf-8', errors='ignore'))
print("STDERR:\n", stderr.read().decode('utf-8', errors='ignore'))
ssh.close()
