import os, sys, time, paramiko, socket
sys.stdout.reconfigure(encoding='utf-8')

USER = "root"
PASS = "root"
LOCAL_DIR = r"Gay_Nguoi_Mu\firmware\maixcam_app"
REMOTE_DIR = "/root/maixcam_app"

import concurrent.futures

def connect_ssh():
    # Neu truyen IP tu dong lenh (vi du: python sync_and_test_maixcam.py 192.168.110.55)
    if len(sys.argv) > 1 and sys.argv[1].count('.') == 3:
        target_ip = sys.argv[1].strip()
        print(f"[MAIXCAM] Thu ket noi SSH toi IP chi dinh: {target_ip}...")
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(target_ip, username=USER, password=PASS, timeout=3.0)
            print(f"[MAIXCAM] >>> KET NOI THANH CONG TOI {target_ip}! <<<\n")
            return client, target_ip
        except Exception as e:
            print(f"[MAIXCAM] Loi ket noi {target_ip}: {e}")

    candidates = ["10.225.139.1", "10.225.138.1", "143.0.4.1", "192.168.1.3"]
    for ip in candidates:
        print(f"[MAIXCAM] Thu ket noi SSH USB/RNDIS toi {ip}...")
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, username=USER, password=PASS, timeout=1.5)
            print(f"[MAIXCAM] >>> KET NOI THANH CONG TOI {ip}! <<<\n")
            return client, ip
        except Exception:
            pass

    # Tu dong quet mang Wi-Fi hien tai cua may tinh (192.168.110.x)
    print("[MAIXCAM] Dang quet nhanh tren mang Wi-Fi tim MaixCAM...")
    local_ips = []
    try:
        s_test = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s_test.connect(("8.8.8.8", 80))
        my_local_ip = s_test.getsockname()[0]
        s_test.close()
        prefix = ".".join(my_local_ip.split(".")[:3])
        local_ips = [f"{prefix}.{i}" for i in range(1, 255) if f"{prefix}.{i}" != my_local_ip]
    except Exception:
        pass

    def _test_ssh(ip):
        try:
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c.connect(ip, username=USER, password=PASS, timeout=1.0)
            return c, ip
        except Exception:
            return None

    if local_ips:
        with concurrent.futures.ThreadPoolExecutor(max_workers=60) as ex:
            futures = [ex.submit(_test_ssh, ip) for ip in local_ips]
            for f in concurrent.futures.as_completed(futures):
                res = f.result()
                if res is not None:
                    client, ip = res
                    print(f"[MAIXCAM] >>> TIM THAY VA KET NOI MAIXCAM QUA WIFI TAI {ip}! <<<\n")
                    return client, ip

    raise ConnectionError(
        f"Khong the ket noi SSH toi MaixCAM!\n"
        f"- Neu dung cap USB: Hay cam cap USB Type-C (co truyen du lieu) tu MaixCAM vao PC.\n"
        f"- Neu dung WiFi: Hay kiem tra xem MaixCAM da ket noi WiFi 'Nha Tro 5' chua, hoac truyen IP truc tiep: python sync_and_test_maixcam.py <IP_MAIXCAM>"
    )

ssh, HOST = connect_ssh()

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

print(f"[MAIXCAM] Dang dong bo toan bo thu muc {LOCAL_DIR} len {REMOTE_DIR}...")
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
        else:
            print(f"  == Khop size: {rem_file}")

sftp.close()
print("[MAIXCAM] >> ĐỒNG BỘ TOÀN BỘ CODE & ASSETS THÀNH CÔNG! <<\n")

# CAI DAT KHOI DONG CUNG HE THONG (AUTOSTART KHI CAM DIEN / BOOT)
print("--- [1] CAI DAT TU KHOI DONG KHI CAM DIEN (AUTOSTART) ---")
autostart_cmd = """
cat <<'EOF' > /etc/init.d/S99smartcane
#!/bin/sh
case "$1" in
  start)
    echo "[AUTOSTART] Khoi dong SmartCane main.py..."
    fuser -k -9 /dev/snd/* 2>/dev/null
    amixer -c 1 cset numid=1 1 2>/dev/null
    amixer -c 1 cset numid=3 0 2>/dev/null
    amixer -c 1 cset numid=2 32,32 2>/dev/null
    amixer -q sset DAC 100% unmute 2>/dev/null
    amixer -q sset Speaker 100% unmute 2>/dev/null
    # Doi WiFi driver va USB RNDIS khoi dong hoan toan (tranh race condition khi boot tu Type-C)
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
    echo "Usage: $0 {start|stop|restart}"
    exit 1
    ;;
esac
exit 0
EOF
chmod +x /etc/init.d/S99smartcane
"""
try:
    ssh.exec_command(autostart_cmd, timeout=5)
    print(">> ĐÃ CÀI ĐẶT AUTOSTART THÀNH CÔNG! (CẮM ĐIỆN LÀ MAIXCAM TỰ CHẠY)")
except Exception as ea:
    print("[AUTOSTART WARN]:", ea)

# KHOI DONG LAI CHUONG TRINH CHINH MAIN.PY TREN MAIXCAM
print("\n--- [2] KHOI DONG MAIN.PY TREN MAIXCAM ---")
start_cmd = """
# Giai phong va Unmute ALSA am thanh phan cung
fuser -k -9 /dev/snd/* 2>/dev/null
amixer -c 1 cset numid=1 1 2>/dev/null
amixer -c 1 cset numid=3 0 2>/dev/null
amixer -c 1 cset numid=2 32,32 2>/dev/null
amixer -q sset DAC 100% unmute 2>/dev/null
amixer -q sset Speaker 100% unmute 2>/dev/null

# Buoc 1: SIGTERM de global_cleanup() chay -> cam.close() giai phong soph_vpss kernel module
kill -TERM $(pgrep -f main.py) 2>/dev/null
sleep 3
# Buoc 2: SIGKILL du phong neu van con process
killall -9 python3 2>/dev/null
# Buoc 3: Cho kernel module soph_vpss settle hoan toan
sleep 3
sync
# Buoc 4: Khoi dong lai
nohup python3 -u /root/maixcam_app/main.py >/tmp/main.log 2>&1 &
sleep 2
ps | grep python | grep -v grep
"""
try:
    stdin, stdout, stderr = ssh.exec_command(start_cmd, timeout=20)
    res = stdout.read().decode().strip()
    print("[TIEN TRINH DANG CHAY]:\n", res)
    print("\n>>> MAIXCAM DA KHOI DONG CHUONG TRINH MAIN.PY THANH CONG! <<<")
except Exception as e:
    print("[RUN ERROR]:", e)

# [3] STREAMING LOG MAIXCAM THOI GIAN THUC
print("\n" + "="*65)
print("  STREAMING LOG MAIXCAM THỜI GIAN THỰC (LIVE LOG STREAM)")
print("  • Quét tiền VND, đọc chữ OCR, bấm nút sẽ hiển thị liên tục bên dưới")
print("  • Dữ liệu cũng được đồng thời truyền qua Serial sang ESP32")
print("  • Bấm Ctrl+C để dừng xem log (MaixCAM vẫn tiếp tục chạy)")
print("="*65 + "\n")

try:
    stdin, stdout, stderr = ssh.exec_command("tail -n 25 -f /tmp/main.log", get_pty=True)
    for line in iter(stdout.readline, ""):
        line_clean = line.strip()
        if not line_clean:
            continue
        if "[TIEN]" in line_clean or "[TIỀN]" in line_clean:
            print(f"\033[92;1m{line_clean}\033[0m")
        elif "[OCR]" in line_clean:
            print(f"\033[93;1m{line_clean}\033[0m")
        elif "[NUT" in line_clean or "[NÚT" in line_clean or "[BTN" in line_clean:
            print(f"\033[96;1m{line_clean}\033[0m")
        elif "[CHE DO]" in line_clean or "[CHẾ ĐỘ]" in line_clean:
            print(f"\033[95;1m{line_clean}\033[0m")
        elif "ERR" in line_clean or "ERROR" in line_clean:
            print(f"\033[91;1m{line_clean}\033[0m")
        else:
            print(f"  {line_clean}")
except KeyboardInterrupt:
    print("\n[LOG] Đã dừng theo dõi log trên Terminal. MaixCAM vẫn tiếp tục chạy ngầm!")
finally:
    try:
        ssh.close()
    except:
        pass

