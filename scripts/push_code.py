import paramiko
import time

LOCAL_FILE = r"Gay_Nguoi_Mu\firmware\maixcam_app\main.py"
REMOTE_FILE = "/root/maixcam_app/main.py"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("10.225.139.1", username="root", password="root", timeout=5)

# Cập nhật DNS & hosts trên MaixCAM
ssh.exec_command('''
echo "nameserver 1.1.1.1" > /etc/resolv.conf
echo "nameserver 192.168.110.5" >> /etc/resolv.conf
echo "nameserver 8.8.8.8" >> /etc/resolv.conf
grep -q "api.ocr.space" /etc/hosts || echo "94.130.69.140 api.ocr.space" >> /etc/hosts
''')

# Cập nhật script khởi động S99smartcane có lệnh restart và python3 -u (unbuffered)
s99_content = """#!/bin/sh
case "$1" in
  start)
    echo "[AUTOSTART] Khoi dong SmartCane main.py..."
    amixer -q sset Master 100% unmute 2>/dev/null
    amixer -q sset Playback 100% unmute 2>/dev/null
    amixer -q sset DAC 100% unmute 2>/dev/null
    amixer -q sset Speaker 100% unmute 2>/dev/null
    amixer -q cset numid=1 100% 2>/dev/null
    sleep 1
    nohup python3 -u /root/maixcam_app/main.py >/tmp/main.log 2>&1 &
    ;;
  stop)
    killall -9 python3 2>/dev/null
    ;;
  restart)
    killall -9 python3 2>/dev/null
    sleep 1
    amixer -q sset Master 100% unmute 2>/dev/null
    amixer -q sset Speaker 100% unmute 2>/dev/null
    nohup python3 -u /root/maixcam_app/main.py >/tmp/main.log 2>&1 &
    ;;
  *)
    echo "Usage: $0 {start|stop|restart}"
    exit 1
    ;;
esac
exit 0
"""
sftp = ssh.open_sftp()
with sftp.file('/etc/init.d/S99smartcane', 'w') as f:
    f.write(s99_content)
ssh.exec_command('chmod +x /etc/init.d/S99smartcane')

print("[1] Upload file main.py moi...")
sftp.put(LOCAL_FILE, REMOTE_FILE)
sftp.close()
print(">> Upload hoan tat!")

print("[2] Khoi dong lai main.py tren MaixCAM...")
ssh.exec_command("/etc/init.d/S99smartcane restart")
time.sleep(3)

print("[3] Kiem tra process va log...")
stdin, stdout, stderr = ssh.exec_command("ps | grep python")
print("[PROCESSES]:\n", stdout.read().decode())

time.sleep(2)
stdin, stdout, stderr = ssh.exec_command("tail -n 25 /tmp/main.log")
print("[LOG]:\n", stdout.read().decode())
ssh.close()
print(">> HOAN TAT DONG BO!")
