import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=3.0)

cmd = """python3 - << 'EOF'
from maix import pinmap
import serial, time

print("--- THIET LAP PINMAP UART1 ---")
pinmap.set_pin_function("A18", "UART1_RX")
pinmap.set_pin_function("A19", "UART1_TX")

print("A18 now:", pinmap.get_pin_function("A18"))
print("A19 now:", pinmap.get_pin_function("A19"))

s = serial.Serial('/dev/ttyS1', 9600, timeout=0.5)

print("\n--- DANG LANG NGHE DU LIEU TU ESP32 TRONG 6 GIAY... ---")
start = time.time()
while time.time() - start < 6.0:
    if s.in_waiting:
        line = s.readline()
        print(f"[NHAN TU ESP32]: {line}")
    time.sleep(0.05)

print("\n--- THU GUI LENH SANG ESP32 ---")
s.write(b"T:150\n")
s.flush()
time.sleep(0.5)
if s.in_waiting:
    resp = s.read(s.in_waiting)
    print(f"[PHAN HOI KHI GUI T:150]: {resp}")
else:
    print("[CHUA CO PHAN HOI KHI GUI T:150]")

s.close()
EOF
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
