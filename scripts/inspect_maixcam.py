import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=5)

def run(cmd):
    print(">>> " + cmd)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    if out:
        print("STDOUT:\n", out)
    if err:
        print("STDERR:\n", err)

run("cat /maixapp/apps/benchmark/best3out.mud")
run("ls -la /maixapp/apps/benchmark/")
run("ls -la /root/models/")
ssh.close()
