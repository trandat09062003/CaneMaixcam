import olefile, re

ole = olefile.OleFileIO('gaynguoimu/Sheet2.SchDoc')
data = ole.openstream('FileHeader').read()
pairs = re.findall(rb'\|([A-Za-z0-9_]+)=([^\|]+)', data)
records = []
cur = {}
for k, v in pairs:
    ks = k.decode('ascii', errors='ignore')
    vs = v.decode('latin1', errors='ignore').split('\x00')[0]
    if ks == 'RECORD':
        if cur: records.append(cur)
        cur = {'RECORD': vs}
    else: cur[ks] = vs
if cur: records.append(cur)

for i in range(645, 695):
    if i < len(records):
        print(f"[{i:>3}] RECORD={records[i].get('RECORD'):<3} {records[i]}")
