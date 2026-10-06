import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=4)

cmd = """python3 - << 'EOF'
import sys, os
print("1. import modules")
from maix import pinmap, audio
print("2. pinmap UART1")
pinmap.set_pin_function("A18", "UART1_RX")
pinmap.set_pin_function("A19", "UART1_TX")
print("3. open serial")
import serial
ser = serial.Serial('/dev/ttyS1', 9600, timeout=1)
ser.write(b"HELLO\\n")
print("4. init_npu_detector")
from maix import nn
mud = '/root/maixcam_app/models/vnd_currency.mud'
if os.path.exists(mud):
    print("MUD exists, trying to load...")
    try:
        det = nn.YOLOv8(mud)
        print("YOLOv8 loaded successfully!")
    except Exception as e:
        print("YOLOv8 error:", e)
print("5. camera test")
from maix import camera
c = camera.Camera(640, 480)
print("Camera OK!")
c.close()
EOF
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())
ssh.close()
