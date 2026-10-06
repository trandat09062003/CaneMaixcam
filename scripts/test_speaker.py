import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

USER = "root"
PASS = "root"
IPS = ["10.225.139.1", "10.225.138.1", "143.0.4.1", "192.168.1.3"]

def connect_ssh(retries=6):
    for attempt in range(retries):
        for ip in IPS:
            try:
                c = paramiko.SSHClient()
                c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                c.connect(ip, username=USER, password=PASS, timeout=2.5)
                print(f"[TEST LOA] Ket noi thanh cong toi MaixCAM tai {ip}!")
                return c, ip
            except Exception:
                pass
        time.sleep(1.0)
    print("[TEST LOA] Chua ket noi duoc MaixCAM qua SSH. Hay kiem tra cap USB Type-C!")
    return None, None

ssh, host = connect_ssh()
if not ssh:
    sys.exit(1)

# Tam dung main.py va giai phong sound card ALSA de chuan bi test
print("[TEST LOA] Giai phong sound card ALSA de chuan bi test...")
stdin, stdout, stderr = ssh.exec_command(
    "/etc/init.d/S99smartcane stop; "
    "killall -9 python3 2>/dev/null; "
    "killall -9 aplay 2>/dev/null; "
    "fuser -k -9 /dev/snd/* 2>/dev/null; "
    "sync; sleep 1.5"
)
stdout.channel.recv_exit_status()

remote_code = """import os, sys, time, wave, gc
from maix import audio

print("=== [1] KIEM TRA & UNMUTE ALSA MIXER (CARD 1: cv182xa_dac) ===")
unmute_cmds = [
    "amixer -c 1 sset DAC 32",
    "amixer -c 1 cset numid=3 0",
    "amixer -c 1 cset numid=1 1",
    "amixer -c 1 cset numid=2 32,32",
    "amixer -q sset DAC 100% unmute",
    "amixer -q sset Speaker 100% unmute"
]
for cmd in unmute_cmds:
    os.system(cmd + " 2>/dev/null")
os.system("amixer -c 1")
print(">> Da unmute & bat max am luong ALSA mixer Card 1!")

audio_dir = "/root/maixcam_app/audio"

def play_audio_file(filepath, label=""):
    if not os.path.exists(filepath):
        print(">> Khong tim thay file: " + filepath)
        return False
    
    print(">> Dang phat: " + os.path.basename(filepath) + " (" + label + ")...")
    try:
        with wave.open(filepath, 'rb') as wf:
            dur = float(wf.getnframes()) / float(wf.getframerate())
    except Exception:
        dur = 1.0

    p = None
    for attempt in range(4):
        try:
            p = audio.Player(filepath)
            p.volume(100)
            p.play()
            time.sleep(dur + 0.12)
            print(">> Phat thanh cong: " + os.path.basename(filepath) + "!")
            return True
        except Exception as e:
            if attempt < 3:
                time.sleep(0.3)
                os.system("fuser -k -9 /dev/snd/* 2>/dev/null")
                continue
            else:
                print(">> Loi phat am thanh (" + filepath + "): " + str(e))
                return False
        finally:
            if p is not None:
                try:
                    del p
                except Exception:
                    pass
                p = None
            gc.collect()
            time.sleep(0.1)
    return False

print("\\n=== [2] TEST PHAT AM THANH KHOI DONG ===")
play_audio_file(os.path.join(audio_dir, "system_ready.wav"), "Am khoi dong")

print("\\n=== [3] TEST PHAT GIONG DOC TIEN ===")
play_audio_file(os.path.join(audio_dir, "hai_muoi_nghin_dong.wav"), "20.000 Dong")

print("\\n=== [4] TEST TIENG BEEP CANH BAO ===")
play_audio_file(os.path.join(audio_dir, "warn_beep.wav"), "Tieng bip canh bao")

print("\\n>>> HOAN TAT TOAN BO TEST LOA! <<<")
"""

sftp = ssh.open_sftp()
with sftp.open('/root/run_test_spk.py', 'w') as f:
    f.write(remote_code)
sftp.close()

print("[TEST LOA] Dang chay chuong trinh test am thanh tren MaixCAM...")
stdin, stdout, stderr = ssh.exec_command("python3 -u /root/run_test_spk.py", get_pty=True)
for line in iter(stdout.readline, ""):
    print(line, end="")

# Sau khi test xong, khoi dong lai dich vu SmartCane main.py tren MaixCAM
print("\n[TEST LOA] Khoi dong lai chuong trinh chinh SmartCane main.py tren MaixCAM...")
ssh.exec_command("/etc/init.d/S99smartcane restart")
time.sleep(2)
print("[TEST LOA] He thong da tro lai hoat dong binh thuong!")

ssh.close()
