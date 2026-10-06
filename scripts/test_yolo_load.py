import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=5)

def run_test(cmd):
    print("Testing:", cmd)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    print("STDOUT:", out)
    print("STDERR:", err)

run_test("python3 -c \"from maix import nn; print('Imported nn'); d = nn.YOLOv5(model='/maixapp/apps/benchmark/best3out.mud', dual_buff=False); print('Loaded successfully:', d)\"")

ssh.close()
