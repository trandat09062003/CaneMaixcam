import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.225.139.1', username='root', password='root', timeout=5)

test_code = """
import requests, json
OCR_API_URL = 'https://api.ocr.space/parse/image'
OCR_API_KEY = 'K82394297788957'

try:
    print('Testing OCR Space connection...')
    resp = requests.get(OCR_API_URL, timeout=5)
    print('GET STATUS:', resp.status_code)
except Exception as e:
    print('OCR ERROR:', e)
"""
stdin, stdout, stderr = ssh.exec_command(f'python3 -c "{test_code}"')
print("OUTPUT:\n", stdout.read().decode())
print("ERR:\n", stderr.read().decode())
ssh.close()
