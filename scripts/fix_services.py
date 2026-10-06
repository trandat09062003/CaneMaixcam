import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.138.1', username='root', password='root', timeout=5)

def run(cmd):
    print("=" * 40)
    print("CMD: " + cmd)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    if out: print("OUT:\n" + out.strip())
    if err: print("ERR:\n" + err.strip())

# Check running processes and services
run("ps aux | grep -E 'python|smartcane'")
run("systemctl status smartcane")

# STOP and DISABLE smartcane service
run("systemctl stop smartcane")
run("systemctl disable smartcane")
run("rm -f /etc/systemd/system/smartcane.service")
run("systemctl daemon-reload")

# Kill any leftover python processes holding the camera
run("killall -9 python3 2>/dev/null || true")

# Check dmesg for camera / ION memory
run("dmesg | tail -n 25")

ssh.close()
print("FINISHED!")
