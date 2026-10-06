#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script tu dong upload toan bo ma nguon, mo hinh AI va am thanh len Sipeed MaixCAM
"""

import os
import sys
import time
import socket
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

LOCAL_APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Gay_Nguoi_Mu", "firmware", "maixcam_app")
LOCAL_AUDIO_DIR = os.path.join(LOCAL_APP_DIR, "audio")

REMOTE_APP_DIR = "/root/maixcam_app"
REMOTE_AUDIO_DIR = "/root/audio"
REMOTE_MODELS_DIR = "/root/models"
REMOTE_APP_STORE_DIR = "/maixapp/apps/smartcane"

def find_maixcam_ip():
    """Tim kiem dia chi IP cua MaixCAM tren mang noi bo USB"""
    candidates = ["10.225.139.1", "10.225.138.1", "143.0.4.1", "192.168.1.3"]
    # Doc card mang RNDIS/NCM tren Windows neu co
    try:
        import subprocess
        out = subprocess.check_output(['powershell', '-Command', 'Get-NetIPAddress -InterfaceAlias "*Ethernet*" | Select-Object -ExpandProperty IPAddress']).decode('utf-8', errors='ignore')
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("10."):
                parts = line.split(".")
                parts[-1] = "1"
                ip = ".".join(parts)
                if ip not in candidates:
                    candidates.insert(0, ip)
    except Exception:
        pass

    for ip in candidates:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            res = s.connect_ex((ip, 22))
            s.close()
            if res == 0:
                return ip
        except Exception:
            pass
    return None

def p(msg):
    print(msg, flush=True)

def main():
    p("=" * 60)
    p("  TIEN TRINH NAI VA DONG BO HE THONG LEN SIPEED MAIXCAM")
    p("=" * 60)

    p("[1/5] Dang tim kiem ket noi MaixCAM qua USB...")
    maixcam_ip = find_maixcam_ip()
    retry_count = 0
    while not maixcam_ip:
        retry_count += 1
        p(f"      Chua thay MaixCAM (lan thu {retry_count}). Vui long cam cap USB Type-C cua MaixCAM vao PC...")
        time.sleep(2)
        maixcam_ip = find_maixcam_ip()
        if retry_count > 60:
            p("[ERR] Qua thoi gian cho. Vui long kiem tra lai ket noi cap USB cua MaixCAM.")
            return False

    p(f"[OK] Phat hien MaixCAM tai dia chi IP: {maixcam_ip}")

    # Ket noi SSH
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(maixcam_ip, username='root', password='root', timeout=5)
    except Exception as e:
        p(f"[ERR] Khong the dang nhap SSH vao MaixCAM: {e}")
        return False

    sftp = ssh.open_sftp()

    def run_cmd(cmd):
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode('utf-8', errors='ignore')
        err = stderr.read().decode('utf-8', errors='ignore')
        return out.strip(), err.strip()

    p("[2/5] Khoi tao thu muc he thong tren MaixCAM...")
    for d in [REMOTE_APP_DIR, REMOTE_AUDIO_DIR, REMOTE_MODELS_DIR, REMOTE_APP_STORE_DIR]:
        run_cmd(f"mkdir -p {d}")

    p("[3/5] Upload ma nguon & cac file cau hinh...")
    # Upload main.py
    main_py_local = os.path.join(LOCAL_APP_DIR, "main.py")
    if os.path.exists(main_py_local):
        sftp.put(main_py_local, f"{REMOTE_APP_DIR}/main.py")
        sftp.put(main_py_local, f"{REMOTE_APP_STORE_DIR}/main.py")
        p(f"      + Upload: main.py -> {REMOTE_APP_DIR}/main.py")

    # Upload app.yaml
    app_yaml_local = os.path.join(LOCAL_APP_DIR, "app.yaml")
    if os.path.exists(app_yaml_local):
        sftp.put(app_yaml_local, f"{REMOTE_APP_DIR}/app.yaml")
        sftp.put(app_yaml_local, f"{REMOTE_APP_STORE_DIR}/app.yaml")
        p(f"      + Upload: app.yaml")

    p("[4/5] Upload toan bo am thanh giong noi tieng Viet (MP3 & WAV)...")
    if os.path.exists(LOCAL_AUDIO_DIR):
        for fname in os.listdir(LOCAL_AUDIO_DIR):
            if fname.endswith(".mp3") or fname.endswith(".wav"):
                lpath = os.path.join(LOCAL_AUDIO_DIR, fname)
                rpath = f"{REMOTE_AUDIO_DIR}/{fname}"
                sftp.put(lpath, rpath)
                p(f"      + Audio: {fname}")

    # Chuyen doi MP3 sang WAV tren thiet bi de audio.Player phat chuan nhat
    p("      Dang chuyen doi am thanh chuan 16kHz mono WAV...")
    run_cmd(f"cd {REMOTE_AUDIO_DIR} && for f in *.mp3; do ffmpeg -i \"$f\" -y -ar 16000 -ac 1 \"${{f%.*}}.wav\" 2>/dev/null; done")

    p("[5/5] Upload va cau hinh mo hinh AI NPU YOLOv8 nhan dien tien VND moi nhat...")
    local_models_dir = os.path.join(LOCAL_APP_DIR, "models")
    if os.path.exists(local_models_dir):
        for fname in os.listdir(local_models_dir):
            lpath = os.path.join(local_models_dir, fname)
            rpath = f"{REMOTE_MODELS_DIR}/{fname}"
            sftp.put(lpath, rpath)
            p(f"      + Upload Model: {fname} -> {rpath}")

    # Dam bao file vnd_currency.mud tren MaixCAM su dung dung model cvimodel
    mud_content = f"""[basic]
type = cvimodel
model = {REMOTE_MODELS_DIR}/model_9384.cvimodel

[extra]
model_type = yolov8
type = detector
input_type = rgb
labels = 1000, 10000, 100000, 2000, 20000, 200000, 5000, 50000, 500000
mean = 0, 0, 0
scale = 0.00392156862745098, 0.00392156862745098, 0.00392156862745098
"""
    with sftp.open(f"{REMOTE_MODELS_DIR}/vnd_currency.mud", "w") as f:
        f.write(mud_content)
    # Ghi them file model_9384.mud de an toan
    with sftp.open(f"{REMOTE_MODELS_DIR}/model_9384.mud", "w") as f:
        f.write(mud_content)
    p("      + Da cap nhat mo hinh YOLO NPU (Model 9384): /root/models/vnd_currency.mud")


    p("      Cai dat dich vu tu dong chay khi bat nguon (smartcane.service)...")
    service_content = f"""[Unit]
Description=Smart Cane Main Application for Blind Persons
After=multi-user.target

[Service]
Type=simple
WorkingDirectory={REMOTE_APP_DIR}
ExecStart=/usr/bin/python3 {REMOTE_APP_DIR}/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    with sftp.open("/etc/systemd/system/smartcane.service", "w") as f:
        f.write(service_content)

    run_cmd("systemctl daemon-reload")
    run_cmd("systemctl enable smartcane.service")
    p("      + Da kich hoat dich vu smartcane.service!")

    sftp.close()
    ssh.close()

    p("\n" + "=" * 60)
    p("  HOAN TAT TOAN BO QUA TRINH NAI & CAU HINH SIPEED MAIXCAM!")
    p("=" * 60)
    p("Cac tinh nang da san sang tren thiet bi:")
    p("  1. Mo hinh AI NPU Nhan dien menh gia tien VND: 10k -> 500k")
    p("  2. Nhan dang chu tieng Viet (OCR)")
    p("  3. Toan bo he thong giong noi tieng Viet da nap day du")
    p("  4. Giao tiep UART 9600 baud voi ESP32 da duoc kich hoat")
    p("  5. Tu dong chay khi khoi dong (standalone) hoac chay truc tiep tu MaixVision")
    p("=" * 60)
    return True

if __name__ == "__main__":
    main()
