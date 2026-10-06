import os, sys, time, paramiko

LOCAL_FILE = r"Gay_Nguoi_Mu\firmware\maixcam_app\main.py"
REMOTE_FILE = "/root/maixcam_app/main.py"
HOST = "10.225.139.1"
USER = "root"
PASS = "root"

print(f"[1] Ket noi SSH toi {HOST}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=5)

print(f"[2] Upload file {LOCAL_FILE} -> {REMOTE_FILE}...")
sftp = ssh.open_sftp()
sftp.put(LOCAL_FILE, REMOTE_FILE)
sftp.close()
print(">> Upload hoan tat!")

print("[3] Goi lenh sync & reboot de giai phong hardware ISP...")
try:
    ssh.exec_command("sync; reboot")
except:
    pass
ssh.close()

print("[4] Cho MaixCAM khoi dong lai trong 15 giay...")
time.sleep(15)

# Thu ket noi lai sau reboot
connected = False
for attempt in range(10):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOST, username=USER, password=PASS, timeout=3)
        connected = True
        print(f">> MaixCAM da khoi dong xong o lan thu {attempt+1}!")
        break
    except:
        time.sleep(2)

if not connected:
    print("Chua the ket noi lai, vui long kiem tra nguon USB.")
    sys.exit(1)

print("\n--- KIEM TRA PROCESS VA LOG MAIN.PY ---")
stdin, stdout, stderr = ssh.exec_command("ps | grep python")
print("[PROCESSES]:\n", stdout.read().decode())

time.sleep(3)
stdin, stdout, stderr = ssh.exec_command("tail -n 25 /tmp/main.log")
print("[LOG /tmp/main.log]:\n", stdout.read().decode())
ssh.close()
