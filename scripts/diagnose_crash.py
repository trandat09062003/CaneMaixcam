import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=4)

def run(cmd):
    print("=" * 40)
    print("CMD:", cmd)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='ignore').strip()
    err = stderr.read().decode('utf-8', errors='ignore').strip()
    if out: print("STDOUT:\n", out)
    if err: print("STDERR:\n", err)

run("cat /root/kata/model_9383.mud")
run("ls -l /root/kata/")

# Test loading with python directly and capture traceback
run("python3 -c \"import os; os.chdir('/root/kata'); from maix import nn; print('Imported nn'); d = nn.YOLOv8('/root/kata/model_9383.mud'); print('YOLOv8 OK:', d)\"")
run("python3 -c \"from maix import nn; m = nn.NN('/root/kata/model_9383.cvimodel'); print('NN cvimodel OK:', m)\"")

ssh.close()
