import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=3)

def run_ssh(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print('CMD:', cmd)
    out = stdout.read().decode('utf-8', errors='ignore').strip()
    err = stderr.read().decode('utf-8', errors='ignore').strip()
    if out: print('STDOUT:\n', out)
    if err: print('STDERR:\n', err)

# Check model file exists and is executable/readable
run_ssh('ls -lh /root/kata/')

# Test with gdb to see exact crash backtrace
run_ssh('gdb -batch -ex "run" -ex "bt" --args python3 -c "from maix import nn; d = nn.YOLOv8(model=\'/root/kata/model_9383.mud\', dual_buff=False)"')

ssh.close()
