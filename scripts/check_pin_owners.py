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

pins = [r for r in records if r.get('RECORD') == '2']
print("Number of pins:", len(pins))
owners = set(p.get('OwnerIndex') for p in pins)
sorted_owners = sorted([int(o) for o in owners if o and o.isdigit()])

for o in sorted_owners:
    if o < len(records):
        lib = records[o].get('LibReference', '')
        print(f"Owner {o}: Lib={lib}")
