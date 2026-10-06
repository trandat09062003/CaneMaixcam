import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=3)

def run(cmd):
    print(">>>", cmd)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print("STDOUT:\n", stdout.read().decode('utf-8', errors='ignore').strip())
    print("STDERR:\n", stderr.read().decode('utf-8', errors='ignore').strip())

# Test python loading
run("python3 -c \"from maix import nn; print(dir(nn))\"")
run("python3 -c \"from maix import nn; d = nn.YOLOv8(model='/root/kata/model_9383.mud'); print('Loaded:', d)\"")
run("dmesg | tail -n 20")

ssh.close()
