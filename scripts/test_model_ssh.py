import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=5)

def run(cmd):
    print(">>> " + cmd)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    print("STDOUT:\n", out)
    print("STDERR:\n", err)

# Check processes
run("ps aux | grep -E 'python|maix'")

# Run isolated python test
run('python3 -c "from maix import nn; print(\'Loading...\'); d = nn.YOLOv5(model=\'/maixapp/apps/benchmark/best3out.mud\'); print(\'Success:\', d)"')

ssh.close()
