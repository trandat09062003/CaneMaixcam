import os
import sys

# Test on MaixCAM:
# Create /root/models/test.mud with relative model filename:
# best3out_int8_cv181x.cvimodel
# and copy the cvimodel into the SAME directory!

import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=5)

sftp = ssh.open_sftp()
with sftp.open("/root/test_cvimodel.py", "w") as f:
    f.write('''import os, sys
print("=== Python test running ===")
os.system("free -m")
from maix import nn
print("Imported maix.nn successfully")
p = "/maixapp/apps/benchmark/best3out_int8_cv181x.cvimodel"
print("Loading:", p)
try:
    m = nn.NN(p)
    print("nn.NN SUCCESS:", m)
except Exception as e:
    print("nn.NN EXCEPTION:", e)
''')
sftp.close()

stdin, stdout, stderr = ssh.exec_command('python3 /root/test_cvimodel.py; dmesg | tail -n 10')
print("STDOUT:\n", stdout.read().decode('utf-8', errors='ignore'))
print("STDERR:\n", stderr.read().decode('utf-8', errors='ignore'))
ssh.close()

