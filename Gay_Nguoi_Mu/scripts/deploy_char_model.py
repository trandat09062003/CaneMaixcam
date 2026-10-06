#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script tự động đẩy file char_ocr.cvimodel lên MaixCAM ngay khi bạn tải từ MaixHub về.
"""
import os
import sys
import paramiko

candidates = [
    r"Gay_Nguoi_Mu\firmware\maixcam_app\models\char_ocr.cvimodel",
    r"Gay_Nguoi_Mu\models\char_ocr.cvimodel",
    r"char_ocr.cvimodel"
]

target_file = None
for c in candidates:
    if os.path.exists(c):
        target_file = c
        break

if not target_file:
    # Tìm bất kỳ file .cvimodel mới nào trong thư mục tải về hoặc maixhub
    for root, dirs, files in os.walk("."):
        for f in files:
            if f.endswith(".cvimodel") and "vnd" not in f and "938" not in f:
                target_file = os.path.join(root, f)
                break

if not target_file:
    print("[CHƯA TÌM THẤY] Bạn chưa copy file char_ocr.cvimodel vào thư mục dự án.")
    print("Vui lòng tải từ MaixHub về, đổi tên thành 'char_ocr.cvimodel' và đặt vào thư mục:")
    print("  Gay_Nguoi_Mu/firmware/maixcam_app/models/char_ocr.cvimodel")
    sys.exit(1)

print(f"[TIM THAY] Tim thay model cvimodel tai: {target_file}")
remote_path = "/root/maixcam_app/models/char_ocr.cvimodel"

for ip in ["10.225.139.1", "10.225.138.1", "143.0.4.1", "192.168.1.3"]:
    try:
        print(f"[MAIXCAM] Thu ket noi toi {ip}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username="root", password="root", timeout=3)
        print(f"[MAIXCAM] Ket noi thanh cong toi {ip}!")
        sftp = ssh.open_sftp()
        print(f"[UPLOAD] Dang day file model {target_file} len {remote_path}...")
        sftp.put(target_file, remote_path)
        sftp.close()
        print("[UPLOAD THANH CONG] Da nạp model char_ocr.cvimodel vao NPU MaixCAM!")
        
        # Khoi dong lai chuong trinh
        ssh.exec_command("killall -9 python3 2>/dev/null; sleep 1; nohup python3 -u /root/maixcam_app/main.py >/tmp/main.log 2>&1 &")
        print("[KHOI DONG] Da khoi dong lai he thong Smart Cane voi model moi!")
        ssh.close()
        sys.exit(0)
    except Exception as e:
        pass

print("[LOI] Khong the ket noi SSH toi MaixCAM qua cong USB. Vui long kiem tra cap!")
