import os, sys, time, paramiko, socket, subprocess

USER = "root"
PASS = "root"
LOCAL_DIR = r"Gay_Nguoi_Mu\firmware\maixcam_app"
REMOTE_DIR = "/root/maixcam_app"

def find_maixcam_ip():
    # 1. Kiem tra cac IP USB RNDIS pho bien
    usb_ips = ["10.225.139.1", "10.225.138.1", "143.0.4.1", "192.168.1.3"]
    for ip in usb_ips:
        try:
            s = socket.create_connection((ip, 22), timeout=0.2)
            s.close()
            return ip
        except:
            pass

    # 2. Kiem tra IP WiFi trong arp table
    try:
        out = subprocess.getoutput("arp -a")
        for line in out.splitlines():
            p = line.split()
            if len(p) >= 2 and p[0].startswith("192.168.110.") and p[0] != "192.168.110.255":
                try:
                    s = socket.create_connection((p[0], 22), timeout=0.2)
                    s.close()
                    return p[0]
                except:
                    pass
    except:
        pass
    return None

print("[AUTO-SYNC] Dang cho MaixCAM ket noi qua cap USB Type-C hoac WiFi...")
maix_ip = None
while not maix_ip:
    maix_ip = find_maixcam_ip()
    if maix_ip:
        break
    time.sleep(1.0)

print(f"[AUTO-SYNC] >>> TIM THAY MAIXCAM TAI IP: {maix_ip}! <<<")
time.sleep(1.0)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(maix_ip, username=USER, password=PASS, timeout=5)
sftp = ssh.open_sftp()

def ensure_remote_dir(path):
    parts = path.strip("/").split("/")
    cur = ""
    for p in parts:
        cur += "/" + p
        try:
            sftp.stat(cur)
        except IOError:
            sftp.mkdir(cur)

print(f"[AUTO-SYNC] Dang dong bo code va 47 file am thanh chuan 16kHz...")
ensure_remote_dir(REMOTE_DIR)

for root, dirs, files in os.walk(LOCAL_DIR):
    if "__pycache__" in root:
        continue
    rel_path = os.path.relpath(root, LOCAL_DIR)
    rem_sub = REMOTE_DIR if rel_path == "." else os.path.join(REMOTE_DIR, rel_path).replace("\\", "/")
    ensure_remote_dir(rem_sub)
    for f in files:
        loc_file = os.path.join(root, f)
        rem_file = os.path.join(rem_sub, f).replace("\\", "/")
        loc_sz = os.path.getsize(loc_file)
        need_upload = True
        try:
            r_stat = sftp.stat(rem_file)
            if r_stat.st_size == loc_sz:
                need_upload = False
        except:
            need_upload = True

        if need_upload:
            print(f"  -> Upload: {rem_file}")
            sftp.put(loc_file, rem_file)

sftp.close()
print("[AUTO-SYNC] Dong bo file hoan tat!")

# Cai dat autostart S99smartcane
s99_cmd = """
cat <<'EOF' > /etc/init.d/S99smartcane
#!/bin/sh
case "$1" in
  start)
    fuser -k -9 /dev/snd/* 2>/dev/null
    amixer -c 1 cset numid=1 1 2>/dev/null
    amixer -c 1 cset numid=3 0 2>/dev/null
    amixer -c 1 cset numid=2 32,32 2>/dev/null
    amixer -q sset DAC 100% unmute 2>/dev/null
    amixer -q sset Speaker 100% unmute 2>/dev/null
    sleep 5
    nohup python3 -u /root/maixcam_app/main.py >/tmp/main.log 2>&1 &
    ;;
  stop)
    killall -9 python3 2>/dev/null
    fuser -k -9 /dev/snd/* 2>/dev/null
    ;;
  restart)
    killall -9 python3 2>/dev/null
    fuser -k -9 /dev/snd/* 2>/dev/null
    sleep 1
    amixer -c 1 cset numid=1 1 2>/dev/null
    amixer -c 1 cset numid=3 0 2>/dev/null
    amixer -c 1 cset numid=2 32,32 2>/dev/null
    nohup python3 -u /root/maixcam_app/main.py >/tmp/main.log 2>&1 &
    ;;
  *)
    exit 1
    ;;
esac
exit 0
EOF
chmod +x /etc/init.d/S99smartcane
"""
ssh.exec_command(s99_cmd)

# Khoi dong lai chuong trinh
print("[AUTO-SYNC] Khoi dong lai SmartCane main.py...")
start_cmd = """
fuser -k -9 /dev/snd/* 2>/dev/null
amixer -c 1 cset numid=1 1 2>/dev/null
amixer -c 1 cset numid=3 0 2>/dev/null
amixer -c 1 cset numid=2 32,32 2>/dev/null
killall -9 python3 2>/dev/null
sleep 2
nohup python3 -u /root/maixcam_app/main.py >/tmp/main.log 2>&1 &
"""
ssh.exec_command(start_cmd)
time.sleep(2)
stdin, stdout, stderr = ssh.exec_command("ps | grep python | grep -v grep")
print("[TIEN TRINH DANG CHAY]:\n", stdout.read().decode())
ssh.close()
print(">>> DA CAP NHAT VA KHOI DONG THANH CONG! <<<")
