import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=4)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='ignore'))

run("find / -name '*.cvimodel' 2>/dev/null")
run("find / -name '*.mud' 2>/dev/null")

ssh.close()
