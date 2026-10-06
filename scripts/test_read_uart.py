import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=5.0)

script = """
import time
from maix import pinmap
import serial

pinmap.set_pin_function("A18", "UART1_RX")
pinmap.set_pin_function("A19", "UART1_TX")

s = serial.Serial('/dev/ttyS1', 9600, timeout=1)
s.reset_input_buffer()

print("LISTENING...")
for _ in range(10):
    time.sleep(0.3)
    n = s.in_waiting
    if n > 0:
        data = s.read(n)
        print("RECV:", repr(data))
        break
else:
    print("NO DATA")

s.close()
"""

stdin, stdout, stderr = ssh.exec_command(f'python3 -c "{script}"')
print("OUTPUT:\n" + stdout.read().decode())
err = stderr.read().decode()
if err:
    print("ERROR:\n" + err)
ssh.close()
