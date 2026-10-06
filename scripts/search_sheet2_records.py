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

for idx, r in enumerate(records):
    found = False
    for k, v in r.items():
        if any(w in v for w in ['SW1', 'BT1', 'IP5306', 'KEY']):
            found = True
            break
    if found:
        print(f"Rec {idx} (type {r.get('RECORD')}): {r}")
