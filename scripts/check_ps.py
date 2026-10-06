import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('10.225.139.1', username='root', password='root', timeout=5)
    stdin, stdout, stderr = ssh.exec_command('ps -o pid,stat,args')
    print("Process list:")
    print(stdout.read().decode())
    ssh.close()
except Exception as e:
    print("Error:", e)
