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

run("cat /usr/bin/yolov5s_224_int8.mud")
run("cat /maixapp/apps/benchmark/best3out.mud")
run('python3 -c "from maix import nn; d = nn.YOLOv5(model=\'/usr/bin/yolov5s_224_int8.mud\'); print(\'Builtin YOLOv5 loaded OK!:\', d)"')

ssh.close()
