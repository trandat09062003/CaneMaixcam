import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=5)

def run(cmd):
    print(">>> " + cmd)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    if out: print("STDOUT:\n", out.strip())
    if err: print("STDERR:\n", err.strip())

run("python3 -c 'import maix; print(maix.__file__)'")
run("find /usr -name '*maix*' 2>/dev/null | grep -E '\.so'")

ssh.close()
