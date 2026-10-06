#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import paramiko, time, sys
sys.stdout.reconfigure(encoding="utf-8")

CANDIDATES = ["10.225.139.1", "10.225.138.1", "143.0.4.1", "192.168.1.3"]
ssh = None
for ip in CANDIDATES:
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(ip, username="root", password="root", timeout=2.5)
        print(f"[OK] SSH thanh cong: {ip}")
        ssh = c
        break
    except Exception:
        pass

if not ssh:
    print("[ERROR] Khong ket noi duoc MaixCam!")
    sys.exit(1)

def run(cmd, timeout=8):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="ignore").strip()
    err = stderr.read().decode(errors="ignore").strip()
    return out, err

print("\n=== BUOC 1: ALSA Sound Cards ===")
out, _ = run("aplay -l 2>&1")
print(out or "(khong co output)")

print("\n=== BUOC 2: Mixer Card 0 va 1 ===")
for card in [0, 1]:
    out, _ = run(f"amixer -c {card} contents 2>&1 | head -20")
    print(f"--- Card {card} ---\n{out or '(khong ton tai)'}")

print("\n=== BUOC 3: Force unmute Card 1 ===")
for cmd in ["amixer -c 1 cset numid=1 1", "amixer -c 1 cset numid=2 32,32"]:
    out, err = run(cmd)
    print(f"  {cmd}: {'OK' if not err else err[:60]}")

print("\n=== BUOC 4: Thu aplay ===")
test_wav = "/root/maixcam_app/audio/system_ready.wav"
for device in ["hw:1,0", "hw:0,0", "default"]:
    print(f"\n[TEST] aplay -D {device}")
    out, err = run(f"aplay -D {device} -q {test_wav} 2>&1; echo EXIT:$?", timeout=10)
    print(f"  {out}")
    time.sleep(1)

print("\n=== BUOC 5: maix.audio.Player ===")
out, _ = run(
    "python3 -c \"from maix import audio; import time; "
    "p=audio.Player('/root/maixcam_app/audio/system_ready.wav'); "
    "p.volume(100); p.play(); time.sleep(3); del p; print('AUDIO OK')\" 2>&1",
    timeout=12
)
print(out or "(khong co output)")

print("\n=== BUOC 6: Log cuoi main.py ===")
out, _ = run("tail -40 /tmp/main.log 2>&1")
print(out or "(khong co log)")

print("\n=== BUOC 7: Tim loi audio trong log ===")
out, _ = run("grep -i 'audio\\|alsa\\|aplay\\|loi\\|error\\|warn' /tmp/main.log 2>/dev/null | tail -20")
print(out or "(khong co loi audio)")

ssh.close()
print("\n[DONE] Debug xong!")
