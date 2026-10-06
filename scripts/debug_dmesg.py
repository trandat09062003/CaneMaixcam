import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=5)

def run(cmd):
    print(">>> " + cmd)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    if out: print("STDOUT:\n", out)
    if err: print("STDERR:\n", err)

# Check dmesg for crash logs
run("dmesg | tail -n 30")

# Check model_tool or cvi tools
run("which model_tool || which cvi_dump || which cvimodel_dump")

# Run benchmark main.py directly to see if it also crashes!
run("python3 /maixapp/apps/benchmark/main.py")

ssh.close()
