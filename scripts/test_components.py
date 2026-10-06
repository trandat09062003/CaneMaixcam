import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=5)

def run(name, code):
    print("=== TEST: " + name + " ===")
    stdin, stdout, stderr = ssh.exec_command(f"python3 -c \"{code}\"")
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    if out: print("STDOUT:\n", out.strip())
    if err: print("STDERR:\n", err.strip())

run("Import maix", "import maix; print('maix version:', maix.__version__)")
run("Camera test", "from maix import camera; c = camera.Camera(320, 240); print('Camera OK:', c); img = c.read(); print('Read img:', img.size())")
run("Display test", "from maix import display; d = display.Display(); print('Display OK:', d)")
run("Audio test", "from maix import audio; print('Audio module OK')")
run("NN check models", "import os; print('benchmark files:', os.listdir('/maixapp/apps/benchmark/'))")
run("NN generic load", "from maix import nn; print('nn loaded'); m = nn.NN('/maixapp/apps/benchmark/best3out_int8_cv181x.cvimodel'); print('NN model loaded:', m)")

ssh.close()
