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

# Record 34 has parameters
for idx, r in enumerate(records):
    if r.get('RECORD') == '34':
        oid = int(r.get('OwnerIndex', '-1'))
        if 0 <= oid < len(records) and r.get('Name') == 'Designator':
            records[oid]['Designator'] = r.get('Text')
        if 0 <= oid < len(records) and r.get('Name') == 'Comment':
            records[oid]['Comment'] = r.get('Text')

for idx, r in enumerate(records):
    if r.get('RECORD') == '1':
        print(f"Comp [{idx}]: Des={r.get('Designator')} Comm={r.get('Comment')} Lib={r.get('LibReference')}")
