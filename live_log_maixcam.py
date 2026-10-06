import os
import sys
import time
import socket
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

USER = "root"
PASS = "root"
CANDIDATES = ["10.225.139.1", "10.225.138.1", "143.0.4.1", "192.168.1.3"]

print("=" * 65)
print("  THEO DOI LOG REALTIME MAIXCAM (GAY THONG MINH)")
print("  Tu dong bat app, stream toan bo log AI & nhan dien tien!")
print("=" * 65)

def wait_for_maixcam():
    while True:
        for ip in CANDIDATES:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.6)
                if s.connect_ex((ip, 22)) == 0:
                    s.close()
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(ip, username=USER, password=PASS, timeout=2.0)
                    return client, ip
                s.close()
            except Exception:
                pass
        print("[CHO KET NOI] Dang tim MaixCAM qua USB (Cam cap USB vao may)...", end="\r")
        time.sleep(1.0)

def main():
    while True:
        try:
            ssh, ip = wait_for_maixcam()
            print(f"\n[KET NOI THANH CONG] >>> Da ket noi toi MaixCAM ({ip})! <<<")
            
            # Đảm bảo main.py đang chạy
            check_cmd = "ps | grep python3 | grep main.py | grep -v grep"
            _, stdout, _ = ssh.exec_command(check_cmd)
            running = stdout.read().decode().strip()
            
            if not running:
                print("[SYS] Khoi dong chuong trinh main.py tren MaixCAM...")
                start_cmd = "nohup python3 /root/maixcam_app/main.py >/tmp/main.log 2>&1 &"
                ssh.exec_command(start_cmd)
                time.sleep(1.5)
            else:
                print("[SYS] Chuong trinh main.py da dang chay san tren MaixCAM.")
            
            print("-" * 65)
            print(">>> BAT DAU STREAM LOG REALTIME TU MAIXCAM (Ctrl+C de dung) <<<")
            print("-" * 65)
            
            # Stream log realtime qua tail -f
            stdin, stdout, stderr = ssh.exec_command("tail -n 30 -f /tmp/main.log", get_pty=True)
            
            for line in iter(stdout.readline, ""):
                if not line:
                    break
                if "[TIỀN]" in line_str or "TIEN" in line_str:
                    print(f"\033[92m{line_str}\033[0m") # Màu xanh lá cho nhận diện tiền
                elif "[OCR]" in line_str or "VAN BAN" in line_str:
                    print(f"\033[93m{line_str}\033[0m") # Màu vàng cho đọc chữ
                elif "[NÚT BT" in line_str or "BUTTON" in line_str:
                    print(f"\033[96m{line_str}\033[0m") # Màu xanh lơ cho nút bấm
                elif "[CHẾ ĐỘ]" in line_str:
                    print(f"\033[95m{line_str}\033[0m") # Màu tím cho chế độ
                elif "SOS" in line_str:
                    print(f"\033[91m{line_str}\033[0m") # Màu đỏ cho SOS
                elif "d:" in line_str or "cm" in line_str:
                    print(f"\033[94m{line_str}\033[0m") # Màu xanh dương cho khoảng cách
                else:
                    print(line_str)
            
            ssh.close()
        except KeyboardInterrupt:
            print("\n[DUNG] Da dung theo doi log.")
            break
        except Exception as e:
            print(f"\n[MAT KET NOI] MaixCAM ngat ket noi ({e}). Dang cho ket noi lai...")
            time.sleep(1.5)

if __name__ == "__main__":
    main()
