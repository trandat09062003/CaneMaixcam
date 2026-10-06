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

run("ls -lh /maixapp/apps/benchmark/")
run("cat /maixapp/apps/benchmark/best3out.mud 2>/dev/null || cat /maixapp/apps/benchmark/*.mud 2>/dev/null")
run("python3 -c \"from maix import nn; m = nn.NN('/maixapp/apps/benchmark/best3out_int8_cv181x.cvimodel'); print('PREINSTALLED OK:', m)\"")
run("python3 -c \"from maix import nn; m = nn.YOLOv5('/maixapp/apps/benchmark/best3out.mud'); print('YOLOV5 OK:', m)\"")

ssh.close()
