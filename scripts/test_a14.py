import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
for ip in ['10.225.138.1', '10.225.139.1']:
    try:
        ssh.connect(ip, username='root', password='root', timeout=2)
        print("CONNECTED TO", ip)
        break
    except Exception:
        pass

cmd = """python3 -c "
from maix import pinmap, gpio
print('Pinmap funcs A14:', pinmap.get_pin_functions('A14'))
print('Pinmap current A14:', pinmap.get_pin_function('A14'))
try:
    pinmap.set_pin_function('A14', 'GPIOA14')
    b1 = gpio.GPIO('GPIOA14', gpio.Mode.IN, gpio.Pull.PULL_UP)
    print('b1 GPIOA14 read:', b1.value())
except Exception as e:
    print('b1 err:', e)

try:
    b2 = gpio.GPIO('A14', gpio.Mode.IN, gpio.Pull.PULL_UP)
    print('b2 A14 read:', b2.value())
except Exception as e:
    print('b2 err:', e)
" """
stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
