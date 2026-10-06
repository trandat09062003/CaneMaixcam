import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=4)

def run(cmd):
    print("=" * 40)
    print("CMD:", cmd)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    o = stdout.read().decode('utf-8', errors='ignore').strip()
    e = stderr.read().decode('utf-8', errors='ignore').strip()
    if o: print("STDOUT:\n", o)
    if e: print("STDERR:\n", e)

run("python3 -X faulthandler -c \"import os; os.chdir('/root/kata'); from maix import nn; d = nn.YOLOv8('/root/kata/model_9384.mud')\"")
run("python3 -X faulthandler -c \"from maix import nn; m = nn.NN('/root/kata/model_9384.cvimodel')\"")

ssh.close()
