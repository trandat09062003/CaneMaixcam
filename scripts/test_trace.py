import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=4)

script = """
import sys, linecache

def trace_lines(frame, event, arg):
    if event == 'line' and 'main.py' in frame.f_code.co_filename:
        lineno = frame.f_lineno
        line = linecache.getline(frame.f_code.co_filename, lineno)
        print(f"{lineno:4d}: {line.strip()}", flush=True)
    return trace_lines

sys.settrace(trace_lines)
import runpy
runpy.run_path('/root/maixcam_app/main.py', run_name='__main__')
"""

stdin, stdout, stderr = ssh.exec_command(f'python3 -c "{script}"')
print("OUT:\n", stdout.read().decode())
print("ERR:\n", stderr.read().decode())
ssh.close()
