import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=4)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    o = stdout.read().decode('utf-8', errors='ignore').strip()
    e = stderr.read().decode('utf-8', errors='ignore').strip()
    if o: print("STDOUT:\n", o)
    if e: print("STDERR:\n", e)

run('python3 -c "import cv2; print(\'OpenCV:\', cv2.__version__, \'Has DNN:\', hasattr(cv2, \'dnn\'))"')
run('python3 -c "import onnxruntime; print(onnxruntime.__version__)"')

ssh.close()
